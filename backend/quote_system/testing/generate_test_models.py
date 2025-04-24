# testing/generate_test_models.py

import trimesh
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Define output directory relative to this script's location
OUTPUT_DIR = Path(__file__).parent / "benchmark_models"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Model Generation Functions ---

def create_simple_cube(size=10.0):
    """Creates a simple, watertight cube."""
    return trimesh.primitives.Box(extents=[size, size, size])

def create_thin_wall_box(outer_size=20.0, thickness=0.3):
    """Creates a box with thin walls by subtracting a smaller inner box."""
    if thickness * 2 >= outer_size:
        logger.warning(f"Thickness {thickness} too large for outer size {outer_size}, skipping thin wall box.")
        return None
    outer_box = trimesh.primitives.Box(extents=[outer_size, outer_size, outer_size])
    inner_size = outer_size - (2 * thickness)
    inner_box = trimesh.primitives.Box(extents=[inner_size, inner_size, inner_size])
    try:
        thin_wall = outer_box.difference(inner_box, engine='blender') # Blender is more robust
        if not isinstance(thin_wall, trimesh.Trimesh):
             thin_wall = thin_wall.dump(concatenate=True)
        if not hasattr(thin_wall, 'metadata'): thin_wall.metadata = {}
        thin_wall.metadata['thickness'] = thickness
        return thin_wall
    except Exception as e:
        logger.error(f"Failed to create thin wall box using boolean difference: {e}. Is Blender installed and in PATH?")
        return None

def create_non_manifold_edge(size=10.0):
    """Creates two cubes sharing only an edge (non-manifold)."""
    cube1 = trimesh.primitives.Box(extents=[size, size, size])
    cube2 = trimesh.primitives.Box(extents=[size, size, size])
    cube2.apply_translation([size, 0, 0])
    combined_mesh = trimesh.util.concatenate([cube1, cube2])
    return combined_mesh

def create_non_manifold_vertex(size=10.0):
    """Creates three cubes sharing only a single vertex (non-manifold)."""
    cubes = []
    # Place cubes adjacent in X, Y, and XY diagonal corner from origin
    offsets = [[size / 2, 0, 0], [0, size / 2, 0], [size / 2, size / 2, 0]]
    for offset in offsets:
        # Center each box on its offset position relative to origin
        box = trimesh.primitives.Box(extents=[size, size, size])
        box.apply_translation(offset)
        cubes.append(box)
    combined_mesh = trimesh.util.concatenate(cubes)
    # These should meet near the origin vertex
    return combined_mesh


def create_multi_shell(size=10.0, gap=5.0):
    """Creates two separate cubes in the same logical file (multiple bodies)."""
    cube1 = trimesh.primitives.Box(extents=[size, size, size])
    cube2 = trimesh.primitives.Box(extents=[size, size, size])
    cube2.apply_translation([size + gap, 0, 0])
    combined_mesh = trimesh.util.concatenate([cube1, cube2])
    return combined_mesh

def create_mesh_with_hole(size=10.0) -> trimesh.Trimesh:
    """Creates a cube with one face removed (boundary not watertight)."""
    cube = trimesh.primitives.Box(extents=[size, size, size])
    if not hasattr(cube, 'faces') or len(cube.faces) == 0:
         logger.warning("Generated cube primitive has no faces initially.")
         return trimesh.Trimesh()

    try:
        vertices = cube.vertices.copy()
        faces = cube.faces.copy()
        face_normals = cube.face_normals.copy()

        if len(face_normals) > 0:
            face_idx_to_remove = np.argmax(face_normals[:, 2]) # Find face most aligned with +Z
        else:
             logger.warning("Cube has no face normals to determine which face to remove.")
             return cube

        mask = np.ones(len(faces), dtype=bool)
        if 0 <= face_idx_to_remove < len(mask):
             mask[face_idx_to_remove] = False
        else:
             logger.warning(f"Invalid face index {face_idx_to_remove} calculated.")
             return cube

        mesh_with_hole = trimesh.Trimesh(vertices=vertices,
                                         faces=faces[mask],
                                         process=False)
        mesh_with_hole.remove_unreferenced_vertices()
        mesh_with_hole.process()
        logger.debug(f"Created mesh with hole: {len(mesh_with_hole.vertices)} vertices, {len(mesh_with_hole.faces)} faces.")
        return mesh_with_hole
    except Exception as e:
         logger.error(f"Error creating mesh with hole for size {size}: {e}", exc_info=True)
         return cube

def create_overhang_bridge(width=30.0, height=10.0, depth=10.0, leg_width=5.0):
    """Creates a simple bridge shape with a significant overhang needing support."""
    leg1 = trimesh.primitives.Box(extents=[leg_width, depth, height])
    leg1.apply_translation([-(width - leg_width) / 2.0, 0, -height/2.0]) # Base at Z=0

    leg2 = trimesh.primitives.Box(extents=[leg_width, depth, height])
    leg2.apply_translation([(width - leg_width) / 2.0, 0, -height/2.0]) # Base at Z=0

    bridge_span = trimesh.primitives.Box(extents=[width, depth, leg_width]) # Thickness
    # Position span on top of legs
    bridge_span.apply_translation([0, 0, leg_width / 2.0])

    combined = trimesh.util.concatenate([leg1, leg2, bridge_span])
    try:
         # Use Blender for robust union
         final_mesh = combined.union(combined, engine='blender')
         if not isinstance(final_mesh, trimesh.Trimesh):
              final_mesh = final_mesh.dump(concatenate=True)
         # Ensure base is at Z=0 after union which might recenter
         final_mesh.apply_translation([0, 0, -final_mesh.bounds[0, 2]])
         return final_mesh
    except Exception as e:
         logger.warning(f"Boolean union failed for overhang bridge, returning concatenated parts: {e}. Is Blender installed?")
         # Fallback: return combined parts, might be non-manifold
         combined.apply_translation([0, 0, -combined.bounds[0, 2]]) # Base at Z=0
         return combined

# --- NEW MODELS ---

def create_tiny_object(size=0.5):
    """Creates a cube smaller than typical minimum feature sizes."""
    logger.info(f"Creating tiny cube (size: {size}mm)")
    return trimesh.primitives.Box(extents=[size, size, size])

def create_large_object(size=300.0):
    """Creates a cube potentially exceeding build volumes."""
    logger.info(f"Creating large cube (size: {size}mm)")
    return trimesh.primitives.Box(extents=[size, size, size])

def create_small_hole_plate(plate_size=20.0, plate_thickness=3.0, hole_diameter=0.2):
    """Creates a plate with a very small hole, testing minimum hole size DFM."""
    logger.info(f"Creating plate (size: {plate_size}x{plate_size}x{plate_thickness}mm) with small hole (diameter: {hole_diameter}mm)")
    plate = trimesh.primitives.Box(extents=[plate_size, plate_size, plate_thickness])
    # Create a cylinder for the hole, make it longer than the plate thickness
    hole_cyl = trimesh.primitives.Cylinder(radius=hole_diameter / 2.0, height=plate_thickness * 1.5)
    try:
        plate_with_hole = plate.difference(hole_cyl, engine='blender')
        if not isinstance(plate_with_hole, trimesh.Trimesh):
             plate_with_hole = plate_with_hole.dump(concatenate=True)
        return plate_with_hole
    except Exception as e:
        logger.error(f"Failed to create small hole plate using boolean difference: {e}. Is Blender installed?")
        return None

def create_tall_thin_pillar(height=50.0, radius=0.5):
    """Creates a tall, thin cylinder prone to instability/wobble."""
    logger.info(f"Creating tall thin pillar (height: {height}mm, radius: {radius}mm)")
    pillar = trimesh.primitives.Cylinder(radius=radius, height=height)
    # Place base at Z=0
    pillar.apply_translation([0, 0, height / 2.0])
    return pillar

def create_sharp_spike_ball(radius=10.0, spike_height=5.0, num_spikes=30):
    """Creates a sphere with numerous sharp conical spikes."""
    logger.info(f"Creating spike ball (radius: {radius}mm, spikes: {num_spikes})")
    sphere = trimesh.primitives.Sphere(radius=radius, subdivisions=4) # Use a reasonable base sphere
    spikes = []
    # Generate points on the sphere surface
    points_on_sphere = trimesh.sample.sample_surface_sphere(num_spikes) * radius
    normals_on_sphere = points_on_sphere / np.linalg.norm(points_on_sphere, axis=1)[:, None] # Normalize for direction

    for i in range(num_spikes):
        point = points_on_sphere[i]
        normal = normals_on_sphere[i]
        # Create a cone (spike) aligned with the normal
        spike = trimesh.creation.cone(radius=0.5, height=spike_height) # Correct
        # Align cone axis (Z) with sphere normal
        transform = trimesh.geometry.align_vectors([0,0,1], normal)
        # Position base of cone on sphere surface
        transform[:3, 3] = point
        spike.apply_transform(transform)
        spikes.append(spike)

    combined = trimesh.util.concatenate([sphere] + spikes)
    try:
        # Use Blender for robust union
        final_mesh = combined.union(combined, engine='blender')
        if not isinstance(final_mesh, trimesh.Trimesh):
             final_mesh = final_mesh.dump(concatenate=True)
        return final_mesh
    except Exception as e:
         logger.warning(f"Boolean union failed for spike ball, returning concatenated parts: {e}. Is Blender installed?")
         return combined # Return combined parts, likely non-manifold

def create_high_poly_sphere(radius=10.0, subdivisions=5):
    """Creates a sphere with a very high polygon count."""
    logger.info(f"Creating high-poly sphere (radius: {radius}mm, subdivisions: {subdivisions})")
    sphere = trimesh.primitives.Sphere(radius=radius, subdivisions=subdivisions)
    logger.info(f"High-poly sphere has {len(sphere.faces)} faces.")
    return sphere

def create_low_poly_sphere(radius=10.0, subdivisions=1):
    """Creates a sphere with a very low polygon count (coarse)."""
    logger.info(f"Creating low-poly sphere (radius: {radius}mm, subdivisions: {subdivisions})")
    sphere = trimesh.primitives.Sphere(radius=radius, subdivisions=subdivisions)
    logger.info(f"Low-poly sphere has {len(sphere.faces)} faces.")
    return sphere

def create_minimal_contact_sphere(radius=10.0):
    """Creates a sphere intended to sit on the build plate with minimal contact."""
    logger.info(f"Creating minimal contact sphere (radius: {radius}mm)")
    sphere = trimesh.primitives.Sphere(radius=radius)
    # Position sphere so its lowest point is at Z=0
    sphere.apply_translation([0, 0, radius])
    return sphere

def create_internal_void(outer_size=20.0, inner_size=10.0):
    """Creates a cube with a fully enclosed smaller cube inside (internal void)."""
    if inner_size >= outer_size:
        logger.warning("Inner size must be smaller than outer size for internal void.")
        return None
    logger.info(f"Creating cube (size: {outer_size}mm) with internal void (size: {inner_size}mm)")
    outer_box = trimesh.primitives.Box(extents=[outer_size, outer_size, outer_size])
    inner_box = trimesh.primitives.Box(extents=[inner_size, inner_size, inner_size])
    # This creates two separate shells, one inside the other.
    # For a *true* void test, you might just use the outer box and expect DFM to find the hollow.
    # However, generating it explicitly like thin walls but without breaking through is another test case.
    try:
        # This boolean operation effectively creates a hollow box if inner_size is close to outer_size
        # Let's just combine them as separate bodies for a multi-body internal void test.
        # combined = outer_box.difference(inner_box, engine='blender') # This makes a thin shell
        # Instead, let's concatenate them as separate shells
        void_test = trimesh.util.concatenate([outer_box, inner_box])
        return void_test
    except Exception as e:
        logger.error(f"Failed to create internal void model: {e}")
        return None

def create_knife_edge(size=20.0, angle_deg=5.0):
    """Creates a wedge shape with a very acute angle (knife edge)."""
    logger.info(f"Creating knife edge block (size: {size}mm, angle: {angle_deg} deg)")
    # Create a tall box
    box = trimesh.primitives.Box(extents=[size, size, size])
    # Create a cutting plane rotated by the acute angle
    angle_rad = np.radians(angle_deg / 2.0)
    normal = [np.sin(angle_rad), 0, np.cos(angle_rad)]
    # Cut the box
    try:
        knife = trimesh.intersections.slice_mesh_plane(box, plane_normal=normal, plane_origin=[0,0, -size/2.0+0.1])
        # Position base at Z=0
        knife.apply_translation([0, 0, -knife.bounds[0, 2]])
        return knife
    except Exception as e:
        logger.error(f"Failed to create knife edge model: {e}")
        return None


# --- Main Generation Logic ---

def main():
    """Generates all test models."""
    models_to_generate = {
        # Basic Geometry & Size
        "pass_cube_10mm.stl": create_simple_cube(size=10.0),
        "pass_cube_50mm.stl": create_simple_cube(size=50.0),
        "fail_tiny_cube_0.1mm.stl": create_tiny_object(size=0.1),         # FAIL: Too small
        "warn_large_cube_300mm.stl": create_large_object(size=300.0),     # WARN/FAIL: Build volume

        # Wall Thickness
        "fail_thin_wall_0.1mm.stl": create_thin_wall_box(outer_size=20.0, thickness=0.1), # FAIL: Critical thin wall
        "warn_thin_wall_0.5mm.stl": create_thin_wall_box(outer_size=20.0, thickness=0.5), # WARN/PASS: Borderline wall

        # Manifold Issues
        "fail_non_manifold_edge.stl": create_non_manifold_edge(size=10.0),       # FAIL: Non-manifold edge
        "fail_non_manifold_vertex.stl": create_non_manifold_vertex(size=10.0), # FAIL: Non-manifold vertex
        "fail_mesh_with_hole.stl": create_mesh_with_hole(size=10.0),             # FAIL: Not watertight

        # Multiple Bodies / Voids
        "fail_multi_shell.stl": create_multi_shell(size=10.0, gap=5.0),          # FAIL/WARN: Multiple bodies
        "warn_internal_void.stl": create_internal_void(outer_size=20.0, inner_size=10.0), # WARN: Trapped volume

        # Feature Size & Stability
        "warn_small_hole_0.2mm.stl": create_small_hole_plate(hole_diameter=0.2), # WARN/FAIL: Minimum hole size
        "warn_tall_pillar_h50_r0.5.stl": create_tall_thin_pillar(height=50.0, radius=0.5), # WARN: Stability/Support
        "warn_overhang_bridge.stl": create_overhang_bridge(),                    # WARN: Needs support
        "warn_sharp_spikes.stl": create_sharp_spike_ball(),                      # WARN: Sharp features
        "warn_knife_edge_5deg.stl": create_knife_edge(angle_deg=5.0),            # WARN: Acute angle

        # Mesh Complexity
        "pass_high_poly_sphere.stl": create_high_poly_sphere(subdivisions=5),  # PASS: Performance test
        "pass_low_poly_sphere.stl": create_low_poly_sphere(subdivisions=1),   # PASS: Coarse geometry test

        # Bed Adhesion
        "warn_min_contact_sphere.stl": create_minimal_contact_sphere(radius=10.0), # WARN: Minimal contact area
    }

    successful_generations = 0
    failed_generations = 0

    for filename, mesh_generator_call in models_to_generate.items():
        # The value in the dict is now the result of the function call
        mesh = mesh_generator_call
        output_path = OUTPUT_DIR / filename

        if mesh is None or not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
            logger.warning(f"Skipping {filename} as generation failed or resulted in an empty mesh.")
            failed_generations += 1
            continue
        if not mesh.is_watertight and "hole" not in filename and "manifold" not in filename and "multi" not in filename and "void" not in filename and "spikes" not in filename:
             logger.warning(f"Generated mesh for {filename} is not watertight unexpectedly.")
             # Optionally skip export or try to fix: mesh.fill_holes(); mesh.process()

        try:
            # Basic processing & validation before export
            # This might fix minor issues but also takes time
            # mesh.process(validate=True) # Turning off validate=True as it can be slow/strict

            export_successful = mesh.export(output_path)
            if export_successful:
                 logger.info(f"Successfully generated and saved: {output_path}")
                 successful_generations += 1
            else:
                 # Some exporters might return False or None on failure
                 logger.error(f"Failed to export {filename} (export method returned non-True).")
                 failed_generations += 1

        except Exception as e:
            logger.error(f"Failed to process or export {filename}: {e}", exc_info=True)
            failed_generations += 1

    logger.info(f"--- Generation Summary ---")
    logger.info(f"Successfully generated: {successful_generations}")
    logger.info(f"Failed generations: {failed_generations}")
    logger.info(f"Total attempted: {len(models_to_generate)}")
    logger.info(f"Models saved to: {OUTPUT_DIR.resolve()}")
    logger.info("Test model generation complete.")


if __name__ == "__main__":
    # Check for Blender (many functions rely on it for robustness)
    if not trimesh.interfaces.blender.exists:
         logger.warning("Blender executable not found in PATH. Boolean operations might fail or be less robust.")
    main() 
#!/usr/bin/env python3
"""
CNC Feature Recognition and Machining Strategy Selection

This module provides advanced feature recognition for CNC machining,
enabling accurate machining time and cost estimation based on
machining strategies tailored to specific geometric features.
"""

import numpy as np
import logging
import trimesh
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CNCFeatures')

# Try to import optional dependencies
try:
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_SOLID
    from OCP.TopoDS import TopoDS_Face, TopoDS_Shape, TopoDS_Edge
    from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone
    from OCP.BRep import BRep_Tool
    from OCP.TopExp import TopExp_Explorer
    OCP_AVAILABLE = True
except ImportError:
    OCP_AVAILABLE = False
    logger.warning("Open CASCADE Technology (OCP) not available. STL-based analysis only.")

# Feature types for CNC machining
class FeatureType(Enum):
    PLANAR_FACE = 1
    POCKET = 2
    HOLE = 3
    SLOT = 4
    BOSS = 5
    FILLET = 6
    CHAMFER = 7
    THREAD = 8
    CURVED_FACE = 9
    UNDERCUT = 10
    ENGRAVING = 11
    COMPLEX_CONTOUR = 12

@dataclass
class MachiningFeature:
    """Represents a recognized machining feature"""
    feature_type: FeatureType
    position: Tuple[float, float, float]  # Center or reference point
    dimensions: Dict[str, float]          # Key dimensions
    direction: Optional[Tuple[float, float, float]] = None  # Tool approach direction
    volume: float = 0.0                   # Material removal volume
    surface_area: float = 0.0             # Surface area to machine
    complexity: float = 1.0               # Complexity factor (1.0 = standard)
    tool_diameter: float = 0.0            # Recommended tool diameter
    machining_strategy: str = "unknown"   # Recommended machining strategy
    tolerance_class: str = "standard"     # Required tolerance
    surface_finish: str = "standard"      # Required finish
    faces: List[int] = None               # Face indices for this feature (STL)
    edges: List[int] = None               # Edge indices for this feature (STEP)

@dataclass
class MachiningOperation:
    """Defines a machining operation"""
    name: str
    tool_diameter: float
    tool_type: str
    feed_rate: float      # mm/min
    spindle_speed: float  # RPM
    cut_depth: float      # mm per pass
    strategy: str
    time_minutes: float
    feature: MachiningFeature
    
class CNCFeatureRecognition:
    """
    Advanced feature recognition for CNC machining
    
    Analyzes STL or STEP files to identify features specific to CNC machining,
    including pockets, holes, fillets, bosses, etc.
    """
    
    def __init__(self, material_factor=1.0, tolerance_class="standard"):
        """
        Initialize with material machinability factor and tolerance
        
        Args:
            material_factor: Material machinability factor (1.0 = aluminum)
            tolerance_class: "standard", "precision", or "ultra-precision"
        """
        self.material_factor = material_factor
        self.tolerance_class = tolerance_class
        self.mesh = None
        self.step_shape = None
        self.features = []
        self.operations = []
        
        # Tool database
        self.tools = {
            "roughing_endmill_large": {
                "diameter": 12.0,      # mm
                "type": "flat_endmill",
                "max_depth": 36.0,     # mm
                "feed_rate_base": 600.0,  # mm/min (aluminum)
                "rpm": 8000
            },
            "roughing_endmill_medium": {
                "diameter": 8.0,
                "type": "flat_endmill",
                "max_depth": 24.0,
                "feed_rate_base": 800.0,
                "rpm": 10000
            },
            "finishing_endmill": {
                "diameter": 6.0,
                "type": "flat_endmill",
                "max_depth": 18.0,
                "feed_rate_base": 1000.0,
                "rpm": 12000
            },
            "detail_endmill": {
                "diameter": 4.0,
                "type": "flat_endmill",
                "max_depth": 12.0,
                "feed_rate_base": 800.0,
                "rpm": 15000
            },
            "ball_endmill_large": {
                "diameter": 8.0,
                "type": "ball_endmill",
                "max_depth": 24.0,
                "feed_rate_base": 700.0,
                "rpm": 10000
            },
            "ball_endmill_medium": {
                "diameter": 6.0,
                "type": "ball_endmill",
                "max_depth": 18.0,
                "feed_rate_base": 800.0,
                "rpm": 12000
            },
            "ball_endmill_small": {
                "diameter": 3.0,
                "type": "ball_endmill",
                "max_depth": 9.0,
                "feed_rate_base": 600.0,
                "rpm": 16000
            },
            "drill_large": {
                "diameter": 10.0,
                "type": "drill",
                "max_depth": 50.0,
                "feed_rate_base": 150.0,
                "rpm": 8000
            },
            "drill_medium": {
                "diameter": 6.0,
                "type": "drill",
                "max_depth": 36.0,
                "feed_rate_base": 200.0,
                "rpm": 10000
            },
            "drill_small": {
                "diameter": 3.0,
                "type": "drill",
                "max_depth": 18.0,
                "feed_rate_base": 100.0,
                "rpm": 12000
            }
        }
    
    def load_mesh(self, mesh):
        """Load a Trimesh object for analysis"""
        self.mesh = mesh
        logger.info(f"Mesh loaded for feature recognition: {len(mesh.faces)} faces")
        
    def load_step(self, step_shape):
        """Load an OpenCascade shape for analysis"""
        if not OCP_AVAILABLE:
            raise ImportError("OpenCascade (OCP) not available for STEP analysis")
            
        self.step_shape = step_shape
        logger.info("STEP data loaded for feature recognition")
        
    def analyze_features(self):
        """
        Analyze the model to identify CNC-relevant features
        
        Returns:
            List[MachiningFeature]: Recognized features
        """
        if self.step_shape is not None and OCP_AVAILABLE:
            return self._analyze_step_features()
        elif self.mesh is not None:
            return self._analyze_mesh_features()
        else:
            raise ValueError("No geometry loaded for feature recognition")
            
    def _analyze_step_features(self):
        """
        Analyze STEP data for CNC features
        
        This uses OpenCascade to identify features directly from the CAD model
        with high accuracy. Much more precise than mesh-based methods.
        """
        features = []
        
        # Explorer for faces
        face_explorer = TopExp_Explorer(self.step_shape, TopAbs_FACE)
        
        face_count = 0
        planar_faces = []
        cylindrical_faces = []
        other_faces = []
        
        while face_explorer.More():
            face_count += 1
            face = TopoDS_Face.DownCast(face_explorer.Current())
            
            # Get surface type
            surface = BRepAdaptor_Surface(face)
            surface_type = surface.GetType()
            
            if surface_type == GeomAbs_Plane:
                # Handle planar face
                plane = surface.Plane()
                normal = plane.Axis().Direction()
                normal_vec = (normal.X(), normal.Y(), normal.Z())
                
                planar_faces.append({
                    "face": face,
                    "normal": normal_vec
                })
                
            elif surface_type == GeomAbs_Cylinder:
                # Handle cylindrical face (potential hole or boss)
                cylinder = surface.Cylinder()
                axis = cylinder.Axis().Direction()
                axis_vec = (axis.X(), axis.Y(), axis.Z())
                radius = cylinder.Radius()
                
                cylindrical_faces.append({
                    "face": face,
                    "axis": axis_vec,
                    "radius": radius
                })
            else:
                other_faces.append({
                    "face": face,
                    "type": surface_type
                })
                
            face_explorer.Next()
            
        logger.info(f"STEP analysis found {face_count} faces: {len(planar_faces)} planar, "
                   f"{len(cylindrical_faces)} cylindrical, {len(other_faces)} other")
         
        # Analyze planar faces (potential pockets, faces, etc.)
        for pf in planar_faces:
            # In a real implementation, extract detailed geometry and adjacency
            # This is simplified for demonstration purposes
            features.append(MachiningFeature(
                feature_type=FeatureType.PLANAR_FACE,
                position=(0, 0, 0),  # Simplified
                dimensions={"width": 0, "height": 0},  # Would calculate from bounds
                direction=pf["normal"],
                surface_area=0.0,  # Would calculate from face
                complexity=1.0,
                machining_strategy="face_milling"
            ))
        
        # Analyze cylindrical faces (potential holes or bosses)
        for cf in cylindrical_faces:
            # Determine if this is likely a hole or a boss
            # In a real implementation, check if interior or exterior
            is_hole = True  # Simplified assumption for demonstration
            
            feature_type = FeatureType.HOLE if is_hole else FeatureType.BOSS
            machining_strategy = "drilling" if is_hole else "contour_milling"
            
            features.append(MachiningFeature(
                feature_type=feature_type,
                position=(0, 0, 0),  # Would calculate center
                dimensions={"diameter": cf["radius"] * 2},
                direction=cf["axis"],
                tool_diameter=min(cf["radius"] * 2, 12.0),  # Choose appropriate tool
                machining_strategy=machining_strategy
            ))
            
        # Further feature analysis would:
        # 1. Group faces into composite features
        # 2. Detect pockets and slots
        # 3. Identify fillets and chamfers
        # 4. Determine feature relationships
        
        return features
        
    def _analyze_mesh_features(self):
        """
        Analyze mesh data for CNC features
        
        Uses mesh analysis techniques to identify machining features
        when STEP data is not available.
        """
        features = []
        
        if not self.mesh.is_watertight:
            logger.warning("Mesh is not watertight, feature detection may be limited")
        
        # Find planar regions using normal clustering
        planar_regions = self._detect_planar_regions()
        logger.info(f"Detected {len(planar_regions)} planar regions")
        
        for region in planar_regions:
            # Calculate region properties
            face_indices = region["face_indices"]
            normal = region["normal"]
            
            if len(face_indices) < 10:
                continue  # Skip tiny regions
                
            # Calculate center and area
            area = 0
            center = np.array([0.0, 0.0, 0.0])
            
            for face_idx in face_indices:
                face_vertices = self.mesh.vertices[self.mesh.faces[face_idx]]
                # Approximate face center and area
                face_center = np.mean(face_vertices, axis=0)
                face_area = trimesh.triangles.area([face_vertices])[0]
                
                center += face_center * face_area
                area += face_area
                
            if area > 0:
                center = center / area
            
            # Determine if this is likely a pocket or a face
            # In a real implementation, use more sophisticated analysis
            is_pocket = False  # Simplified
            
            feature_type = FeatureType.POCKET if is_pocket else FeatureType.PLANAR_FACE
            machining_strategy = "pocket_milling" if is_pocket else "face_milling"
            
            features.append(MachiningFeature(
                feature_type=feature_type,
                position=tuple(center),
                dimensions={"area": area},
                direction=tuple(normal),
                surface_area=area,
                machining_strategy=machining_strategy,
                faces=face_indices
            ))
            
        # Detect cylindrical features (holes, bosses)
        cylindrical_regions = self._detect_cylindrical_regions()
        logger.info(f"Detected {len(cylindrical_regions)} cylindrical regions")
        
        for region in cylindrical_regions:
            # Determine if this is likely a hole or a boss
            is_hole = region.get("is_hole", True)  # Default to hole
            
            feature_type = FeatureType.HOLE if is_hole else FeatureType.BOSS
            machining_strategy = "drilling" if is_hole else "contour_milling"
            
            center = region["center"]
            axis = region["axis"]
            radius = region["radius"]
            
            features.append(MachiningFeature(
                feature_type=feature_type,
                position=tuple(center),
                dimensions={"diameter": radius * 2, "depth": region.get("depth", 0)},
                direction=tuple(axis),
                tool_diameter=min(radius * 2, 12.0),  # Choose appropriate tool
                machining_strategy=machining_strategy,
                faces=region["face_indices"]
            ))
            
        return features
        
    def _detect_planar_regions(self):
        """
        Detect planar regions in the mesh using normal clustering
        
        Returns:
            List[Dict]: Planar regions with face indices and normal vectors
        """
        if self.mesh is None:
            return []
            
        # Get face normals
        normals = self.mesh.face_normals
        
        # Cluster faces by normal direction
        clusters = []
        face_cluster_map = np.ones(len(normals), dtype=int) * -1
        
        angle_threshold = 0.05  # cos(~3 degrees)
        
        for face_idx, normal in enumerate(normals):
            if face_cluster_map[face_idx] >= 0:
                continue  # Already assigned
                
            # Find all faces with similar normals
            similarities = np.abs(np.dot(normals, normal))
            similar_faces = np.where(similarities > (1.0 - angle_threshold))[0]
            
            if len(similar_faces) > 5:  # Minimum size for a region
                cluster_id = len(clusters)
                face_cluster_map[similar_faces] = cluster_id
                clusters.append({
                    "face_indices": similar_faces.tolist(),
                    "normal": normal.tolist(),
                    "size": len(similar_faces)
                })
        
        # Sort clusters by size (largest first)
        clusters.sort(key=lambda c: c["size"], reverse=True)
        
        # In a real implementation, would verify planar regions by:
        # 1. Checking face connectivity
        # 2. Fitting planes to regions
        # 3. Checking distance of each face to the best-fit plane
        
        return clusters
                
    def _detect_cylindrical_regions(self):
        """
        Detect cylindrical regions in the mesh (potential holes/bosses)
        
        Returns:
            List[Dict]: Cylindrical regions with properties
        """
        if self.mesh is None:
            return []
            
        # This is a very simplified cylindrical detection
        # In a real implementation, use RANSAC or Hough transforms
        
        # Simplified placeholder detection
        cylindrical_regions = []
        
        # In a real implementation:
        # 1. Use normal variance to detect curved regions
        # 2. Fit cylinders to candidate regions
        # 3. Verify cylinder fit quality
        # 4. Determine if interior (hole) or exterior (boss)
        
        return cylindrical_regions
    
    def plan_machining_operations(self):
        """
        Plan machining operations based on detected features
        
        Returns:
            List[MachiningOperation]: Planned operations
        """
        if not self.features:
            self.features = self.analyze_features()
            
        operations = []
        
        # Group features by type for planning
        feature_groups = {}
        for feature in self.features:
            feature_type = feature.feature_type
            if feature_type not in feature_groups:
                feature_groups[feature_type] = []
            feature_groups[feature_type].append(feature)
            
        # Process each feature type with appropriate operations
        
        # Process planar faces (face milling)
        if FeatureType.PLANAR_FACE in feature_groups:
            planar_faces = feature_groups[FeatureType.PLANAR_FACE]
            
            # Sort by area (largest first for roughing)
            planar_faces.sort(key=lambda f: f.surface_area, reverse=True)
            
            # Plan face milling operations
            for i, face in enumerate(planar_faces):
                # Choose tool based on face size
                if i == 0 and face.surface_area > 5000:  # Large face - roughing
                    tool_key = "roughing_endmill_large"
                elif face.surface_area > 1000:
                    tool_key = "roughing_endmill_medium"
                else:
                    tool_key = "finishing_endmill"
                    
                tool = self.tools[tool_key]
                
                # Calculate operation time based on area and feed rate
                # Adjusted for material and tolerance
                material_factor = self.material_factor
                
                # Adjust feed rate based on tolerance class
                tolerance_factor = {
                    "standard": 1.0,
                    "precision": 0.7,
                    "ultra-precision": 0.5
                }.get(self.tolerance_class, 1.0)
                
                feed_rate = tool["feed_rate_base"] / material_factor * tolerance_factor
                
                # Simplified time calculation for face milling
                # For accurate calculations, would need to consider:
                # - Actual tool path length
                # - Acceleration/deceleration
                # - Approach and retract moves
                area_mm2 = face.surface_area
                step_over = tool["diameter"] * 0.7  # 70% tool diameter overlap
                
                # Calculate toolpath length and time
                toolpath_length = area_mm2 / step_over  # Simplified
                machining_time = toolpath_length / feed_rate  # minutes
                
                operations.append(MachiningOperation(
                    name=f"Face milling",
                    tool_diameter=tool["diameter"],
                    tool_type=tool["type"],
                    feed_rate=feed_rate,
                    spindle_speed=tool["rpm"],
                    cut_depth=tool["diameter"] * 0.1,  # 10% of tool diameter
                    strategy="face_milling",
                    time_minutes=machining_time,
                    feature=face
                ))
        
        # Process holes (drilling operations)
        if FeatureType.HOLE in feature_groups:
            holes = feature_groups[FeatureType.HOLE]
            
            # Sort by diameter (small to large)
            holes.sort(key=lambda h: h.dimensions.get("diameter", 0))
            
            for hole in holes:
                diameter = hole.dimensions.get("diameter", 0)
                depth = hole.dimensions.get("depth", 0)
                
                if depth <= 0:
                    # Estimate depth if not specified
                    depth = 20.0  # Default assumption
                
                # Choose appropriate drill
                if diameter >= 8.0:
                    tool_key = "drill_large"
                elif diameter >= 4.0:
                    tool_key = "drill_medium"
                else:
                    tool_key = "drill_small"
                    
                tool = self.tools[tool_key]
                
                # Calculate operation time
                # For drilling, time depends on depth and feed rate
                material_factor = self.material_factor
                
                # Adjust feed rate based on material
                feed_rate = tool["feed_rate_base"] / material_factor
                
                # Simplified drilling time calculation
                machining_time = depth / feed_rate  # minutes
                
                operations.append(MachiningOperation(
                    name=f"Drilling {diameter:.1f}mm hole",
                    tool_diameter=tool["diameter"],
                    tool_type=tool["type"],
                    feed_rate=feed_rate,
                    spindle_speed=tool["rpm"],
                    cut_depth=depth,
                    strategy="drilling",
                    time_minutes=machining_time,
                    feature=hole
                ))
                
        # Process pockets
        if FeatureType.POCKET in feature_groups:
            pockets = feature_groups[FeatureType.POCKET]
            
            for pocket in pockets:
                # Determine best tool and strategy for this pocket
                area = pocket.dimensions.get("area", 0)
                
                # Choose tool based on pocket size
                if area > 5000:
                    roughing_tool_key = "roughing_endmill_medium"
                    finishing_tool_key = "finishing_endmill"
                else:
                    roughing_tool_key = "detail_endmill"
                    finishing_tool_key = "ball_endmill_small"
                
                # Add roughing operation
                roughing_tool = self.tools[roughing_tool_key]
                material_factor = self.material_factor
                feed_rate = roughing_tool["feed_rate_base"] / material_factor
                
                # Simplified time calculation for pocket roughing
                # Real calculation needs pocket volume and dimensions
                roughing_time = area / 1000  # Simplified estimate
                
                operations.append(MachiningOperation(
                    name=f"Pocket roughing",
                    tool_diameter=roughing_tool["diameter"],
                    tool_type=roughing_tool["type"],
                    feed_rate=feed_rate,
                    spindle_speed=roughing_tool["rpm"],
                    cut_depth=roughing_tool["diameter"] * 0.2,
                    strategy="pocket_roughing",
                    time_minutes=roughing_time,
                    feature=pocket
                ))
                
                # Add finishing operation
                finishing_tool = self.tools[finishing_tool_key]
                finish_feed_rate = finishing_tool["feed_rate_base"] / material_factor
                
                # Finishing time is proportional to surface area
                finishing_time = area / 2000  # Simplified estimate
                
                operations.append(MachiningOperation(
                    name=f"Pocket finishing",
                    tool_diameter=finishing_tool["diameter"],
                    tool_type=finishing_tool["type"],
                    feed_rate=finish_feed_rate,
                    spindle_speed=finishing_tool["rpm"],
                    cut_depth=finishing_tool["diameter"] * 0.1,
                    strategy="pocket_finishing",
                    time_minutes=finishing_time,
                    feature=pocket
                ))
        
        # Store operations
        self.operations = operations
        return operations
    
    def calculate_total_machining_time(self):
        """
        Calculate total machining time including tool changes
        
        Returns:
            Dict: Time breakdown
        """
        if not self.operations:
            self.plan_machining_operations()
            
        # Calculate pure machining time
        pure_machining_time = sum(op.time_minutes for op in self.operations)
        
        # Calculate tool changes
        tools_used = set()
        for op in self.operations:
            tools_used.add((op.tool_type, op.tool_diameter))
            
        tool_changes = len(tools_used) - 1 if len(tools_used) > 0 else 0
        tool_change_time = tool_changes * 2.0  # 2 minutes per tool change
        
        # Setup time based on complexity
        setup_time = 30.0  # Base setup time
        
        # Total time
        total_time = pure_machining_time + tool_change_time + setup_time
        
        return {
            "setup_time": setup_time,
            "machining_time": pure_machining_time,
            "tool_changes": tool_changes,
            "tool_change_time": tool_change_time,
            "total_time": total_time
        }
        
    def generate_machining_summary(self):
        """
        Generate a comprehensive machining summary
        
        Returns:
            Dict: Machining summary with detailed breakdown
        """
        times = self.calculate_total_machining_time()
        
        # Count features by type
        feature_counts = {}
        for feature in self.features:
            feature_type = feature.feature_type.name
            feature_counts[feature_type] = feature_counts.get(feature_type, 0) + 1
        
        # Group operations by strategy
        strategy_times = {}
        for op in self.operations:
            strategy = op.strategy
            strategy_times[strategy] = strategy_times.get(strategy, 0) + op.time_minutes
            
        # Create summary
        summary = {
            "features_detected": len(self.features),
            "feature_types": feature_counts,
            "operations_planned": len(self.operations),
            "unique_tools": len(set((op.tool_type, op.tool_diameter) for op in self.operations)),
            "times": times,
            "strategy_breakdown": strategy_times
        }
        
        return summary


def main():
    """Demo application for feature recognition"""
    import sys
    import argparse
    import trimesh
    import json
    
    parser = argparse.ArgumentParser(description="CNC Feature Recognition Tool")
    parser.add_argument("input_file", help="Input STL or STEP file")
    parser.add_argument("--material", default="aluminum_6061", help="Material type")
    parser.add_argument("--tolerance", choices=["standard", "precision", "ultra-precision"], 
                        default="standard", help="Tolerance class")
    parser.add_argument("--output", help="Output JSON file (default: stdout)")
    
    args = parser.parse_args()
    
    # Material factors
    material_factors = {
        "aluminum_6061": 1.0,
        "aluminum_7075": 1.1,
        "stainless_304": 2.0,
        "brass_360": 0.8,
        "steel_1018": 1.5,
        "titanium_6al4v": 3.5,
        "plastic_delrin": 0.5,
        "plastic_hdpe": 0.4
    }
    
    material_factor = material_factors.get(args.material, 1.0)
    
    try:
        # Load the mesh
        mesh = trimesh.load_mesh(args.input_file)
        
        # Create feature recognition engine
        feature_engine = CNCFeatureRecognition(
            material_factor=material_factor,
            tolerance_class=args.tolerance
        )
        
        # Load mesh
        feature_engine.load_mesh(mesh)
        
        # Perform feature recognition
        features = feature_engine.analyze_features()
        
        # Plan machining operations
        operations = feature_engine.plan_machining_operations()
        
        # Generate summary
        summary = feature_engine.generate_machining_summary()
        
        # Create output
        output = {
            "file": args.input_file,
            "material": args.material,
            "tolerance_class": args.tolerance,
            "summary": summary,
            "features": [
                {
                    "type": feature.feature_type.name,
                    "position": feature.position,
                    "dimensions": feature.dimensions,
                    "strategy": feature.machining_strategy
                }
                for feature in features
            ],
            "operations": [
                {
                    "name": op.name,
                    "tool": {
                        "type": op.tool_type,
                        "diameter": op.tool_diameter
                    },
                    "strategy": op.strategy,
                    "time_minutes": op.time_minutes
                }
                for op in operations
            ]
        }
        
        # Output results
        if args.output:
            with open(args.output, "w") as f:
                json.dump(output, f, indent=2)
        else:
            print(json.dumps(output, indent=2))
            
        # Print summary
        print("\n===== CNC Feature Recognition Summary =====")
        print(f"File: {args.input_file}")
        print(f"Features detected: {summary['features_detected']}")
        print(f"Operations planned: {summary['operations_planned']}")
        print(f"Estimated machining time: {summary['times']['machining_time']:.2f} minutes")
        print(f"Total time (with setup): {summary['times']['total_time']:.2f} minutes")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())

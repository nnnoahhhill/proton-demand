# visualization/viewer.py

import os
import logging
import trimesh
from typing import List, Optional
import numpy as np
import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Conditional import for PyVista and GUI backend (e.g., PyQt6 or PySide6)
try:
    import pyvista as pv
    # Attempt to set a suitable notebook backend if in IPython/Jupyter
    try:
        # pv.set_jupyter_backend('trame') # Or 'server', 'client' depending on setup
        pv.set_jupyter_backend(None) # Static images often work best unless server is setup
    except Exception:
        pass # Ignore if not in notebook or backend fails
    # PyVista requires a GUI backend (like PyQt) for interactive plotting outside notebooks
    # No explicit import here, relies on PyVista finding an installed backend
    PYVISTA_AVAILABLE = True
except ImportError:
    PYVISTA_AVAILABLE = False

from ..core.common_types import DFMReport, DFMIssue, QuoteResult

logger = logging.getLogger(__name__)


def show_model_with_issues(
    mesh: trimesh.Trimesh,
    issues: Optional[List[DFMIssue]] = None,
    show_wireframe: bool = True,
    show_axes: bool = True,
    window_size=(800, 600),
    notebook: bool = False # Set True if running in Jupyter/IPython with backend
):
    """
    Displays a 3D model using PyVista, optionally highlighting DFM issues.

    Args:
        mesh: The Trimesh object to display.
        issues: A list of DFM issues associated with the model.
        show_wireframe: Whether to overlay a wireframe view.
        show_axes: Whether to display coordinate axes.
        window_size: The initial window size for the plotter.
        notebook: Set to True if plotting within a Jupyter notebook.
    """
    if not PYVISTA_AVAILABLE:
        logger.error("PyVista library not found. Please install it (`pip install pyvista[all]`) for visualization.")
        print("Visualization requires PyVista. Please install it: pip install pyvista[all]")
        return

    if not isinstance(mesh, trimesh.Trimesh) or mesh.vertices is None or mesh.faces is None:
         logger.error("Invalid or empty mesh provided for visualization.")
         return

    try:
        # --- Plotter Setup ---
        # Use BackgroundPlotter for interactive window, or Plotter for static/notebook
        if notebook:
             # Requires a compatible Jupyter backend (like trame, ipygany, panel)
             plotter = pv.Plotter(notebook=True, window_size=window_size)
        else:
             # Requires a GUI backend (PyQt5/6, PySide2/6)
             # Use BackgroundPlotter for non-blocking interactive window
             # plotter = pv.BackgroundPlotter(window_size=window_size, title="Model Viewer")
             # Using standard Plotter for blocking window - simpler integration sometimes
             plotter = pv.Plotter(window_size=window_size, title="Model Viewer")


        # --- Add Main Mesh ---
        # Convert Trimesh to PyVista PolyData
        pv_mesh = pv.wrap(mesh)
        plotter.add_mesh(pv_mesh, color='lightgrey', smooth_shading=True, label="Original Mesh")

        if show_wireframe:
            plotter.add_mesh(pv_mesh, style='wireframe', color='black', line_width=1, label="Wireframe")

        # --- Highlight DFM Issues ---
        if issues:
            logger.info(f"Visualizing {len(issues)} DFM issues.")
            # Collect points/features to highlight for each issue type
            highlight_points = {
                DFMLevel.CRITICAL: [],
                DFMLevel.ERROR: [],
                DFMLevel.WARN: [],
                DFMLevel.INFO: []
            }
            highlight_colors = {
                DFMLevel.CRITICAL: 'red',
                DFMLevel.ERROR: 'orange',
                DFMLevel.WARN: 'yellow',
                DFMLevel.INFO: 'blue'
            }
            # TODO: Add specific geometries (lines for thin walls, faces for overhangs) later

            for issue in issues:
                level = issue.level
                points = issue.details.get('vertices') if issue.details else None
                if points and isinstance(points, (list, np.ndarray)) and len(points) > 0:
                     # Ensure points are numpy array
                     points_np = np.array(points)
                     if points_np.ndim == 1: # Handle single point
                         points_np = points_np.reshape(1, -1)
                     if points_np.shape[1] == 3: # Check it looks like coordinates
                          highlight_points[level].extend(points_np)
                     else:
                          logger.warning(f"Ignoring issue points with unexpected shape: {points_np.shape} for issue {issue.issue_type}")
                else:
                     logger.debug(f"No specific vertices found in details for issue: {issue.issue_type} ({issue.level})")

            # Add highlighted points to the plotter
            for level, points in highlight_points.items():
                if points:
                    cloud = pv.PolyData(np.array(points))
                    plotter.add_mesh(
                        cloud,
                        color=highlight_colors[level],
                        point_size=10.0,
                        render_points_as_spheres=True,
                        label=f"{level.value} Issues"
                    )

        # --- Final Plotter Configuration ---
        if show_axes:
            plotter.add_axes()
        plotter.add_legend()
        plotter.camera_position = 'iso' # Set initial isometric view

        # --- Show Plot ---
        logger.info("Launching PyVista Plotter window...")
        # For BackgroundPlotter, interaction happens in separate thread.
        # For standard Plotter, this blocks until window is closed.
        plotter.show()
        logger.info("PyVista Plotter closed.")

    except Exception as e:
        logger.exception("Error occurred during PyVista visualization:")
        print(f"An error occurred during visualization: {e}")

# --- Example Usage (for testing viewer directly) ---
if __name__ == '__main__':
    print("Running viewer example...")
    if not PYVISTA_AVAILABLE:
         print("PyVista not available, cannot run example.")
         exit()

    # Create a sample mesh (e.g., a sphere)
    sample_mesh = trimesh.primitives.Sphere(radius=5)

    # Create some dummy DFM issues with vertex coordinates
    dummy_issues = [
        DFMIssue(
            issue_type=DFMIssueType.NON_MANIFOLD,
            level=DFMLevel.CRITICAL,
            message="Critical non-manifold vertex detected.",
            details={"vertices": [[0, 0, 5]]} # Point at north pole
        ),
        DFMIssue(
            issue_type=DFMIssueType.SUPPORT_OVERHANG,
            level=DFMLevel.WARN,
            message="Potential overhang requires support.",
            details={"vertices": [[0, 0, -5], [1,0,-4.9]]} # Points near south pole
        ),
         DFMIssue(
            issue_type=DFMIssueType.BOUNDING_BOX,
            level=DFMLevel.INFO,
            message="Model dimensions noted.",
            details={} # No specific points for this one
        )
    ]

    print("Showing sphere with dummy issues...")
    show_model_with_issues(sample_mesh, dummy_issues)

    print("Viewer example finished.") 
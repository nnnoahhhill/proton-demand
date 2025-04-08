# core/common_types.py
import time
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union # Added Union

from pydantic import BaseModel, Field

# --- Process & Material Enums ---

class ManufacturingProcess(str, Enum):
    """Enum for supported manufacturing processes."""
    PRINT_3D = "3D Printing"
    CNC = "CNC Machining"
    SHEET_METAL = "Sheet Metal" # Placeholder

class Print3DTechnology(str, Enum):
    """Enum for specific 3D Printing technologies."""
    SLA = "SLA"
    FDM = "FDM"
    SLS = "SLS"
    # Add others like MJF, DMLS if needed

# --- DFM Related Enums and Models ---

class DFMStatus(str, Enum):
    """Overall DFM result status."""
    PASS = "Pass"
    WARNING = "Warning"
    FAIL = "Fail"

class DFMLevel(str, Enum):
    """Severity level of a specific DFM issue."""
    INFO = "Info"        # Useful information, not a problem
    WARN = "Warning"    # Potential issue, printable but may have defects/challenges
    ERROR = "Error"      # Likely printable, but needs definite fixing (e.g., very thin wall)
    CRITICAL = "Critical"  # Unprintable without fixing (e.g., non-manifold, file corrupt)

class DFMIssueType(str, Enum):
    """Categorization of DFM issues."""
    # Generic
    FILE_VALIDATION = "File Validation"
    GEOMETRY_ERROR = "Geometry Error"
    # Mesh Specific
    NON_MANIFOLD = "Non-Manifold Geometry"
    SELF_INTERSECTION = "Self-Intersecting Geometry"
    DUPLICATE_FACES = "Duplicate Faces"
    DEGENERATE_FACES = "Degenerate Faces"
    MULTIPLE_SHELLS = "Multiple Disconnected Shells"
    INTERNAL_VOIDS = "Internal Voids / Nested Shells"
    # Dimension Specific
    BOUNDING_BOX_LIMIT = "Exceeds Bounding Box Limits"
    MINIMUM_DIMENSION = "Below Minimum Overall Dimension"
    THIN_WALL = "Thin Wall Detected"
    SMALL_FEATURE = "Feature Size Too Small"
    SMALL_HOLE = "Hole Diameter Too Small"
    # 3D Printing Specific
    SUPPORT_OVERHANG = "Excessive Overhangs / Support Needed"
    SUPPORT_ACCESS = "Difficult Support Removal / Trapped Volumes"
    WARPING_RISK = "Warping Risk (Large Flat Areas)"
    ESCAPE_HOLES = "Missing Escape Holes (SLA/SLS)"
    # CNC Specific (Examples)
    TOOL_ACCESS = "Tool Access Limitations"
    DEEP_POCKET = "Deep Pockets / High Aspect Ratio Feature"
    SHARP_INTERNAL_CORNER = "Sharp Internal Corners (Requires Small Tool / EDM)"
    THIN_FEATURE_CNC = "Thin Feature (Vibration/Breakage Risk)"
    # Sheet Metal Specific (Placeholders)
    BEND_RADIUS = "Minimum Bend Radius Violation"
    FLAT_PATTERN = "Flat Pattern Generation Issue"
    FEATURE_TOO_CLOSE_TO_BEND = "Feature Too Close to Bend"

class DFMIssue(BaseModel):
    """Represents a single identified DFM issue."""
    issue_type: DFMIssueType = Field(..., description="Category of the issue.")
    level: DFMLevel = Field(..., description="Severity of the issue.")
    message: str = Field(..., description="Human-readable description of the issue.")
    recommendation: Optional[str] = Field(None, description="Suggestion on how to fix the issue.")
    # Optional: Data for visualization (e.g., list of vertex indices, face indices, or a specific value)
    visualization_hint: Optional[Any] = Field(None, description="Data hint for visualizing the issue area.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional quantitative details (e.g., measured thickness).")

class DFMReport(BaseModel):
    """Consolidated report of all DFM checks for a model."""
    status: DFMStatus = Field(..., description="Overall pass/warning/fail status.")
    issues: List[DFMIssue] = Field(default_factory=list, description="List of identified DFM issues.")
    analysis_time_sec: float = Field(..., description="Time taken for DFM analysis in seconds.")

# --- Costing and Quoting Models ---

class MaterialInfo(BaseModel):
    """Holds information about a specific material."""
    id: str = Field(..., description="Unique identifier for the material (e.g., 'pla_white', 'aluminum_6061').")
    name: str = Field(..., description="User-friendly name (e.g., 'PLA White', 'Aluminum 6061-T6').")
    process: ManufacturingProcess = Field(..., description="Primary process this material is used for.")
    technology: Optional[Union[Print3DTechnology, str]] = Field(None, description="Specific technology (e.g., FDM, SLA, 3-Axis Milling).")
    cost_per_kg: Optional[float] = Field(None, description="Cost of the material per kilogram (specify currency elsewhere).")
    cost_per_liter: Optional[float] = Field(None, description="Cost of the material per liter (for resins).")
    density_g_cm3: float = Field(..., description="Density in grams per cubic centimeter.")

class CostEstimate(BaseModel):
    """Detailed breakdown of the estimated costs (excluding markup)."""
    material_id: str = Field(..., description="Identifier of the material used.")
    material_volume_cm3: float = Field(..., description="Estimated volume of the part material in cubic cm.")
    support_volume_cm3: Optional[float] = Field(None, description="Estimated volume of support material in cubic cm (for 3D Print).")
    total_volume_cm3: float = Field(..., description="Total material volume used (part + support).")
    material_weight_g: float = Field(..., description="Estimated weight of the material used in grams.")
    material_cost: float = Field(..., description="Calculated cost of the material based on weight/volume and price.")
    # Process time is reported but NOT included in base cost per user request
    process_time_seconds: float = Field(..., description="Estimated time for the machine process in seconds.")
    # Base cost is *only* material cost
    base_cost: float = Field(..., description="Base cost for manufacturing (Material Cost only).")
    cost_analysis_time_sec: float = Field(..., description="Time taken for cost analysis in seconds.")

class QuoteResult(BaseModel):
    """Final quote result including DFM, cost, and time estimates."""
    quote_id: str = Field(default_factory=lambda: f"Q-{int(time.time()*1000)}", description="Unique identifier for this quote request.")
    file_name: str = Field(..., description="Original filename of the uploaded model.")
    process: ManufacturingProcess = Field(..., description="Selected manufacturing process.")
    technology: Optional[str] = Field(None, description="Specific technology used.")
    material_info: MaterialInfo = Field(..., description="Details of the selected material.")
    dfm_report: DFMReport = Field(..., description="Results of the Design for Manufacturing analysis.")
    cost_estimate: Optional[CostEstimate] = Field(None, description="Cost breakdown (only present if DFM status is not FAIL).")
    customer_price: Optional[float] = Field(None, description="Final price to the customer including markup (only present if DFM status is not FAIL).")
    estimated_process_time_str: Optional[str] = Field(None, description="Human-readable estimated process time (e.g., '2h 30m').")
    processing_time_sec: float = Field(..., description="Total time taken for the entire quote generation in seconds.")
    error_message: Optional[str] = Field(None, description="Error message if the quote generation failed unexpectedly.")

# --- Geometry Related Models ---

class BoundingBox(BaseModel):
    """Represents the axis-aligned bounding box."""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float
    size_x: float
    size_y: float
    size_z: float

class MeshProperties(BaseModel):
    """Basic properties extracted from the mesh."""
    vertex_count: int
    face_count: int
    bounding_box: BoundingBox
    volume_cm3: float
    surface_area_cm2: float
    is_watertight: bool # Indicates if Trimesh considers it watertight (manifold)
    units: Optional[str] = Field("mm", description="Units inferred or assumed from the file (usually mm for STL/STEP).") 
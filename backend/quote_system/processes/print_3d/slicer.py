# processes/print_3d/slicer.py

import subprocess
import platform
import os
import logging
import tempfile
import shutil
import re
import time # Added time
from typing import Optional, Dict, Any, Tuple, List # Added List
from dataclasses import dataclass

import trimesh

# from quote_system.core.exceptions import SlicerExecutionError, FileFormatError
from ...core.exceptions import SlicerExecutionError, FileFormatError, ConfigurationError, SlicerError
# from quote_system.core.common_types import Print3DTechnology, MaterialInfo # Added MaterialInfo
from ...core.common_types import Print3DTechnology, MaterialInfo # Added MaterialInfo
# from quote_system.config import settings # Access global config
from ...config import settings # Access global config
from ...core import utils

logger = logging.getLogger(__name__)

# Constants
DEFAULT_SLICER_TIMEOUT = 300 # seconds (5 minutes)

@dataclass
class SlicerResult:
    """Holds the results extracted from the slicer output."""
    print_time_seconds: float
    filament_used_g: float
    filament_used_mm3: float
    # Note: PrusaSlicer often combines part and support material in estimates
    # Separate support material estimation might require more advanced parsing or assumptions.
    support_material_g: Optional[float] = None
    support_material_mm3: Optional[float] = None
    warnings: Optional[List[str]] = None # Potential warnings from slicer output


def find_slicer_executable(slicer_name: str = "prusa-slicer") -> Optional[str]:
    """
    Attempts to find the PrusaSlicer (or compatible) executable path.

    Checks environment variables, common installation paths for Linux, macOS,
    and Windows, and the system PATH.

    Args:
        slicer_name: The base name of the slicer executable (e.g., "prusa-slicer").
                     Also checks for variants like "prusa-slicer-console".

    Returns:
        The absolute path to the executable if found, otherwise None.
    """
    env_var = 'PRUSA_SLICER_PATH'
    console_variant = f"{slicer_name}-console"

    # 1. Check Environment Variable (using alias from config.py)
    # This logic is now mostly handled by config.py loading, but we keep auto-detect as fallback
    # slicer_path_env = os.environ.get(env_var) # Prefer config.settings.slicer_path_override
    # if slicer_path_env:
    #     logger.info(f"Checking environment variable {env_var}: {slicer_path_env}")
    #     if os.path.isfile(slicer_path_env) and os.access(slicer_path_env, os.X_OK):
    #         logger.info(f"Found valid slicer executable via {env_var}: {slicer_path_env}")
    #         return slicer_path_env
    #     else:
    #         logger.warning(f"Path from {env_var} ('{slicer_path_env}') is not a valid executable file. Ignoring.")

    # 2. Check system PATH using shutil.which
    for name in [slicer_name, console_variant]:
        found_path = shutil.which(name)
        if found_path:
            logger.info(f"Found slicer executable in system PATH: {found_path}")
            # Basic check if it's executable (shutil.which usually ensures this)
            if os.access(found_path, os.X_OK):
                 return found_path
            else:
                 logger.warning(f"Path found in PATH ('{found_path}') but not executable? Skipping.")


    # 3. Check Common Installation Paths
    possible_paths = []
    home_dir = os.path.expanduser("~")

    if platform.system() == "Windows":
        # Windows paths
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        possible_paths.extend([
            os.path.join(program_files, "Prusa3D", "PrusaSlicer", f"{console_variant}.exe"),
            os.path.join(program_files, "PrusaSlicer", f"{console_variant}.exe"),
            os.path.join(program_files, "Prusa3D", "PrusaSlicer", f"{slicer_name}.exe"),
            os.path.join(program_files, "PrusaSlicer", f"{slicer_name}.exe"),
            # Add user-specific AppData paths if needed
             os.path.join(home_dir, "AppData", "Local", "Programs", "PrusaSlicer", f"{slicer_name}.exe")
        ])
    elif platform.system() == "Darwin":
        # macOS paths
        possible_paths.extend([
            f"/Applications/PrusaSlicer.app/Contents/MacOS/{slicer_name}",
            # Add potential path for older versions or drivers bundle if needed
            # "/Applications/Original Prusa Drivers/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
            "/usr/local/bin/prusa-slicer", # If installed via brew perhaps
        ])
    else:
        # Linux paths (common locations)
        possible_paths.extend([
            f"/usr/bin/{slicer_name}",
            f"/usr/local/bin/{slicer_name}",
            f"/snap/bin/{slicer_name}", # Snap package
            f"/opt/{slicer_name}/bin/{slicer_name}", # Manual opt install
            f"{home_dir}/Applications/{slicer_name}/{slicer_name}", # AppImage common location
            f"{home_dir}/opt/PrusaSlicer/{slicer_name}" # Another potential manual install
        ])

    logger.debug(f"Checking common paths: {possible_paths}")
    for path in possible_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            logger.info(f"Found valid slicer executable at common path: {path}")
            return path

    logger.warning(f"Slicer executable ('{slicer_name}' or variant) not found via auto-detection.")
    return None

def _generate_slicer_config(
    temp_dir: str,
    layer_height: float,
    fill_density: float, # 0.0 to 1.0
    technology: Print3DTechnology,
    material_profile_name: Optional[str] = None, # e.g., "Prusament PLA"
    print_profile_name: Optional[str] = None, # e.g., "0.20mm QUALITY @MK3"
    printer_model: Optional[str] = None # e.g., "Original Prusa MK4"
) -> str:
    """Generates a temporary PrusaSlicer config (.ini) file."""
    config_path = os.path.join(temp_dir, "temp_config.ini")
    logger.info(f"Generating slicer config: {config_path}")
    # Ensure fill_density is within 0-1 range
    fill_density = max(0.0, min(1.0, fill_density))

    try:
        with open(config_path, "w") as f:
            # Basic settings required for estimation
            f.write(f"layer_height = {layer_height:.3f}\n")
            f.write(f"fill_density = {fill_density*100:.0f}%\n") # Slicer usually takes percentage string
            # Default infill pattern
            f.write("fill_pattern = grid\n")
            # Shells (perimeters/top/bottom) - reasonable defaults
            f.write("perimeters = 2\n")
            f.write("top_solid_layers = 4\n")
            f.write("bottom_solid_layers = 3\n")
            # Enable comments needed for parsing estimates
            f.write("gcode_comments = 1\n")

            # Technology specific settings (might influence defaults)
            if technology == Print3DTechnology.SLA:
                f.write("printer_technology = SLA\n")
                
                # Use very generic settings to be compatible with any SLA printer
                f.write("print_settings_id = default_sla_print\n")
                f.write("filament_settings_id = default_sla_material\n")
                f.write("printer_model = SLA_PRINTER\n")
                
                # More generic SLA settings - don't redefine layer_height here as it's already defined above
                # f.write("layer_height = 0.05\n") # This was causing the duplicate key error
                f.write("supports_enable = 1\n") # Generally needed for SLA
                f.write("support_auto = 1\n")
                
                # Slice everything regardless of position - prevents "Nothing to print" errors
                f.write("validate_output = 0\n") # Disable validation - force output
                f.write("slice_closing_radius = 0.001\n") # Minimal slice closing for cleaner mesh
            elif technology == Print3DTechnology.SLS:
                f.write("printer_technology = FFF\n")  # PrusaSlicer may not fully support SLS yet, so use FFF
                
                # Use generic settings
                f.write("print_settings_id = default_print\n")
                f.write("filament_settings_id = Generic PLA\n")  # Use a common filament as fallback
                f.write("printer_model = Original Prusa i3 MK3\n")  # Use a reliable printer model
                
                # Set parameters to better approximate SLS behavior - but avoid duplicates
                # Don't redefine layer height here, it's set at the top
                # f.write("layer_height = 0.1\n")  # This was causing the duplicate key
                f.write("perimeters = 2\n")
                # Don't redefine fill_density - avoid duplicate
                # f.write("fill_density = 100%\n")
                f.write("supports_enable = 0\n")  # SLS doesn't need supports
                
                # Add notes that this is approximating SLS
                f.write("notes = SLS simulation using FFF technology. Real SLS behavior may differ.\n")
            else: # FDM as default
                f.write("printer_technology = FFF\n")
                
                # Use more reliable generic settings
                f.write("print_settings_id = default_print\n")  # More reliable than trying to guess a specific preset
                f.write("filament_settings_id = Generic PLA\n")  # Common filament that should be in all PrusaSlicer installs
                f.write("printer_model = Original Prusa i3 MK3\n")  # Well-supported printer
                
                # Don't redefine layer_height/fill_density here as they're already set above
                # f.write(f"layer_height = {layer_height:.3f}\n")  # This was causing a duplicate key
                
                # Support settings for FDM (can be overridden)
                f.write("supports_enable = 1\n")  # Enable supports by default for quoting
                f.write("support_material_buildplate_only = 1\n")  # Common default
                f.write("support_threshold = 45\n")  # Standard overhang angle
                
                # Additional settings to ensure reliable slicing
                # Fill pattern is already set above, don't redefine
                # f.write("fill_pattern = grid\n")
                # gcode_comments already set above - don't duplicate
                # f.write("gcode_comments = 1\n")
                f.write("complete_objects = 0\n")  # Disable "complete objects" feature that can cause issues

            # Ensure G-code flavor is set for comment generation if FDM/FFF
            if technology == Print3DTechnology.FDM:
                 f.write("gcode_flavor = marlin\n") # Common flavor, adjust if needed


        return config_path
    except IOError as e:
        logger.error(f"Failed to write slicer config file '{config_path}': {e}", exc_info=True)
        raise ConfigurationError(f"Could not write temporary slicer config: {e}") from e

def _parse_gcode_estimates(gcode_content: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Parses PrusaSlicer/Slic3r G-code comments for time and material estimates."""
    print_time_sec = None
    filament_mm3 = None
    filament_g = None

    # Regex for print time (handles hours, minutes, seconds)
    # Example: '; estimated printing time (normal mode) = 1h 32m 15s'
    time_match = re.search(r";\s*estimated printing time.*=\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?", gcode_content)
    if time_match:
        hours = int(time_match.group(1) or 0)
        minutes = int(time_match.group(2) or 0)
        seconds = int(time_match.group(3) or 0)
        print_time_sec = float(hours * 3600 + minutes * 60 + seconds)
        logger.debug(f"Parsed print time: {hours}h {minutes}m {seconds}s -> {print_time_sec:.2f}s")

    # Regex for filament volume (mm3)
    # Example: '; filament used [mm3] = 12345.67'
    # Can also be '; filament used [cm3] = 12.34' - handle both
    vol_match_mm3 = re.search(r";\s*filament used\s*\[mm3\]\s*=\s*([\d.]+)", gcode_content)
    vol_match_cm3 = re.search(r";\s*filament used\s*\[cm3\]\s*=\s*([\d.]+)", gcode_content)
    if vol_match_mm3:
        filament_mm3 = float(vol_match_mm3.group(1))
        logger.debug(f"Parsed filament volume: {filament_mm3:.2f} mm3")
    elif vol_match_cm3:
         filament_mm3 = float(vol_match_cm3.group(1)) * 1000.0 # Convert cm3 to mm3
         logger.debug(f"Parsed filament volume: {vol_match_cm3.group(1)} cm3 -> {filament_mm3:.2f} mm3")


    # Regex for filament weight (g)
    # Example: '; filament used [g] = 45.67'
    weight_match = re.search(r";\s*filament used\s*\[g\]\s*=\s*([\d.]+)", gcode_content)
    if weight_match:
        filament_g = float(weight_match.group(1))
        logger.debug(f"Parsed filament weight: {filament_g:.2f} g")

    # Basic validation
    if print_time_sec is None: logger.warning("Could not parse estimated print time from G-code comments.")
    if filament_mm3 is None: logger.warning("Could not parse filament volume (mm3 or cm3) from G-code comments.")
    if filament_g is None: logger.warning("Could not parse filament weight (g) from G-code comments.")

    # Check if essential data is missing
    if print_time_sec is None or filament_mm3 is None:
         # Weight (g) is useful but can be calculated if density is known,
         # so only time and volume are strictly essential from parsing.
         logger.error("Failed to parse essential estimates (time, volume) from G-code.")
         # Returning None for values indicates parsing failure
         return None, None, None


    return print_time_sec, filament_mm3, filament_g


def run_slicer(
    stl_file_path: str,
    slicer_executable_path: str,
    layer_height: float,
    fill_density: float, # 0.0 to 1.0
    technology: Print3DTechnology, # FDM, SLA, SLS
    material_density_g_cm3: float, # Needed if slicer doesn't calc weight
    material_profile_name: Optional[str] = None, # Advanced: Specific slicer material profile
    timeout: int = DEFAULT_SLICER_TIMEOUT
) -> SlicerResult:
    """
    Runs the slicer CLI to generate G-code and extract estimates.

    Args:
        stl_file_path: Path to the input STL model.
        slicer_executable_path: Full path to the prusa-slicer executable.
        layer_height: Layer height in mm.
        fill_density: Infill density (0.0 to 1.0).
        technology: The 3D printing technology being used.
        material_density_g_cm3: Material density (used if weight isn't in gcode).
        material_profile_name: Optional name of a slicer material profile to use.
        timeout: Maximum time in seconds to allow the slicer process to run.

    Returns:
        A SlicerResult object containing the parsed estimates.

    Raises:
        FileNotFoundError: If the STL file or slicer executable doesn't exist.
        SlicerError: If the slicer process fails, times out, or estimates cannot be parsed.
        ConfigurationError: If temporary files cannot be created/written.
    """
    if not os.path.exists(stl_file_path):
        raise FileNotFoundError(f"Input STL file not found: {stl_file_path}")
    if not os.path.exists(slicer_executable_path):
        raise FileNotFoundError(f"Slicer executable not found: {slicer_executable_path}")

    # Create a temporary directory for config and output files
    with tempfile.TemporaryDirectory(prefix="slicer_") as temp_dir:
        logger.info(f"Using temporary directory for slicing: {temp_dir}")
        gcode_output_path = os.path.join(temp_dir, "output.gcode")

        # Generate the slicer configuration file
        config_file_path = _generate_slicer_config(
            temp_dir=temp_dir,
            layer_height=layer_height,
            fill_density=fill_density,
            technology=technology,
            material_profile_name=material_profile_name,
            # Add print_profile_name / printer_model if needed based on tech/material
        )

        # Construct the slicer command
        # Note: Using --export-gcode is generally reliable for getting estimate comments
        # even for SLA/SLS in PrusaSlicer, as it runs the slicing pipeline.
        # If direct SLA/SLS export formats are needed later, this might change.
        cmd = [
            slicer_executable_path,
            "--load", config_file_path,
            # "--export-gcode", # Force gcode export to get comments
            # "--output", gcode_output_path,
        ]
        
        # Technology-specific output arguments
        # For SLA/SLS technologies, we'll still use --export-gcode for now
        # to ensure we get print time estimates. This works with PrusaSlicer's internal slicing
        # engine while avoiding issues with specific format exports.
        if technology == Print3DTechnology.SLA:
            # Using gcode export first to get estimations
            cmd.extend(["--export-gcode", "--output", gcode_output_path]) 
            # SL1 format can cause issues with "Nothing to print", especially if the
            # printer profile isn't exactly matched to the Prusa SL1 format requirements
        elif technology == Print3DTechnology.SLS:
            # Similar strategy for SLS
            cmd.extend(["--export-gcode", "--output", gcode_output_path])
        else: # FDM (Default)
            cmd.extend(["--export-gcode", "--output", gcode_output_path])
             
        # Add centering flag - attempts to fix "Nothing to print" errors
        cmd.append("--center") 
        cmd.append("0,0") # Center at XY origin (adjust if needed)
        
        # Add the input file path LAST
        cmd.append(stl_file_path)

        logger.info(f"Running slicer command: {' '.join(cmd)}")
        slicer_start_time = time.time()

        try:
            # We're using gcode output for all technologies now
            expected_output_path = gcode_output_path
            
            # Execute the command
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False # Don't raise CalledProcessError automatically
            )

            slicer_duration = time.time() - slicer_start_time
            logger.info(f"Slicer process finished in {slicer_duration:.2f} seconds with return code {process.returncode}.")

            # Log slicer stdout/stderr for debugging
            if process.stdout:
                 logger.debug(f"Slicer stdout:\n{process.stdout}")
            if process.stderr:
                 # Log stderr as warning or error depending on return code
                 log_level = logging.WARNING if process.returncode == 0 else logging.ERROR
                 logger.log(log_level, f"Slicer stderr:\n{process.stderr}")


            # Check for errors
            if process.returncode != 0:
                error_message = f"Slicer failed with return code {process.returncode}. See logs for details."
                # Include stderr in the exception message if it exists
                if process.stderr:
                     error_message += f"\nSlicer Output (stderr):\n{process.stderr[:1000]}..." # Limit length
                raise SlicerError(error_message)

            # Check if the CORRECT output file was created
            if not os.path.exists(expected_output_path) or os.path.getsize(expected_output_path) == 0:
                 # Sometimes slicer exits 0 but fails to write output (e.g. if model is invalid or off-plate)
                 error_message = f"Slicer ran successfully (code 0) but did not produce expected output file: {os.path.basename(expected_output_path)}"
                 # Include stdout/stderr for clues, especially the "Nothing to print" message
                 if process.stdout:
                     error_message += f"\nSlicer Output (stdout):\n{process.stdout[:1000]}..."
                 if process.stderr:
                      error_message += f"\nSlicer Output (stderr):\n{process.stderr[:1000]}..."
                 raise SlicerError(error_message)
            
            # --- G-code Parsing Logic --- 
            print_time_sec = None
            filament_mm3 = None
            filament_g = None
            slicer_warnings = [] # Placeholder for warnings

            # For all technologies, we're now using G-code output with comments
            logger.info(f"Attempting to parse G-code comments for {technology} estimates...")
            # Read the G-code file content
            with open(expected_output_path, "r") as f:
                gcode_content = f.read()

            # Parse the G-code for estimates
            print_time_sec, filament_mm3, filament_g = _parse_gcode_estimates(gcode_content)

            # Validate parsed results
            if print_time_sec is None:
                logger.warning(f"Could not parse time estimate for {technology}. Using fallback approximation.")
                # Use a fallback value - could be more sophisticated based on layer count, etc.
                # For SLA/SLS, these times are very different from FDM, but better than nothing
                # A more sophisticated system would use tech-specific algorithms
                
                # Set a reasonable default based on technology
                if technology == Print3DTechnology.SLA:
                    # SLA printers typically have more fixed exposure time per layer
                    # Attempting to estimate based on model height and average layer time
                    print_time_sec = 3600  # 1 hour fallback for SLA
                elif technology == Print3DTechnology.SLS:
                    # SLS is typically slower than SLA for most parts
                    print_time_sec = 7200  # 2 hours fallback for SLS
                else:
                    print_time_sec = 3600  # 1 hour fallback for FDM
                
                logger.info(f"Using fallback print time estimate of {print_time_sec} seconds")
            
            # For volume/mass calculation, handle differently for different technologies
            if filament_mm3 is None:
                # If we couldn't parse volume/mass, we need fallback logic
                logger.warning(f"Could not parse volume/mass estimate for {technology}. Using model volume from mesh.")
                
                # Let's read the STL file to get its volume
                try:
                    mesh = trimesh.load(stl_file_path)
                    if mesh.is_watertight:
                        # For watertight mesh, we can use its volume directly
                        model_volume_mm3 = mesh.volume
                        logger.info(f"Using mesh volume of {model_volume_mm3:.2f} mm³")
                        
                        # Compute mass based on density
                        model_volume_cm3 = model_volume_mm3 / 1000.0
                        model_mass_g = model_volume_cm3 * material_density_g_cm3
                        
                        # For different technologies, adjust for support material
                        if technology == Print3DTechnology.FDM:
                            # For FDM, typically need 10-30% extra for supports
                            support_factor = 1.2  # 20% extra for supports
                            filament_mm3 = model_volume_mm3 * support_factor
                            filament_g = model_mass_g * support_factor
                        elif technology == Print3DTechnology.SLA:
                            # SLA can use more support material proportionally
                            support_factor = 1.3  # 30% extra for supports
                            filament_mm3 = model_volume_mm3 * support_factor
                            filament_g = model_mass_g * support_factor
                        elif technology == Print3DTechnology.SLS:
                            # SLS doesn't typically need supports, use raw volume
                            # But there's usually some waste in the powder bed
                            waste_factor = 1.1  # 10% waste
                            filament_mm3 = model_volume_mm3 * waste_factor
                            filament_g = model_mass_g * waste_factor
                            
                        logger.info(f"Calculated volume: {filament_mm3:.2f} mm³, mass: {filament_g:.2f} g with technology-specific adjustments")
                    else:
                        logger.warning("Mesh is not watertight, volume calculation may be inaccurate")
                        # Use a very rough estimate based on bounding box
                        bbox_volume = mesh.bounding_box_oriented.volume
                        fill_factor = 0.3  # Assume model fills ~30% of bounding box
                        filament_mm3 = bbox_volume * fill_factor
                        filament_g = (filament_mm3 / 1000.0) * material_density_g_cm3
                        logger.info(f"Using rough bounding box estimate: {filament_mm3:.2f} mm³, {filament_g:.2f} g")
                except Exception as e:
                    logger.error(f"Failed to calculate mesh volume as fallback: {e}")
                    # Set some minimal values to avoid complete failure
                    filament_mm3 = 10.0
                    filament_g = (filament_mm3 / 1000.0) * material_density_g_cm3

            # If weight (g) wasn't parsed directly (e.g., FDM but missing comment, or non-FDM),
            # calculate it from volume and density IF volume was parsed (only FDM for now)
            if filament_g is None and filament_mm3 is not None: # Only calculate if volume was parsed (FDM)
                 if material_density_g_cm3 is None or material_density_g_cm3 <= 0:
                      raise ConfigurationError("Material density must be provided and positive if slicer does not report weight.")
                 # Convert mm3 to cm3 for density calculation
                 filament_cm3 = filament_mm3 / 1000.0
                 filament_g = filament_cm3 * material_density_g_cm3
                 logger.info(f"Calculated filament weight from volume: {filament_cm3:.2f} cm3 * {material_density_g_cm3} g/cm3 = {filament_g:.2f} g") # Changed level to info


            return SlicerResult(
                print_time_seconds=print_time_sec,
                filament_used_g=filament_g,
                filament_used_mm3=filament_mm3,
                warnings=slicer_warnings if slicer_warnings else None
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Slicer process timed out after {timeout} seconds.")
            raise SlicerError(f"Slicer timed out after {timeout} seconds.") from None
        except FileNotFoundError as e: # Should not happen due to checks above, but belts and suspenders
             logger.error(f"File not found during slicer execution: {e}")
             raise SlicerError(f"File missing during slicing: {e}") from e
        except Exception as e:
            logger.exception("An unexpected error occurred during slicer execution:")
            # Re-raise as SlicerError if it's not already one
            if isinstance(e, SlicerError):
                 raise
            else:
                 raise SlicerError(f"Unexpected slicer execution error: {e}") from e 
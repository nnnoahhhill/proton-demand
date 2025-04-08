# processes/print_3d/slicer.py

import subprocess
import tempfile
import os
import sys
import shutil
import re
import logging
import time # Added time
from typing import Optional, Dict, Any, Tuple, List # Added List
from dataclasses import dataclass

# Assuming core modules are siblings in the package structure
from ...core.exceptions import SlicerError, ConfigurationError
from ...core.common_types import Print3DTechnology

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

    if sys.platform == "win32":
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
    elif sys.platform == "darwin":
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
                # Use generic SLA profiles if specific ones aren't provided
                f.write(f"print_settings_id = {print_profile_name or f'{layer_height:.2f}mm QUALITY @SL1S'}\n") # Example name
                # PrusaSlicer uses filament_settings_id even for SLA materials in config
                f.write(f"filament_settings_id = {material_profile_name or 'Generic SLA Resin'}\n") # Example name
                f.write(f"printer_model = {printer_model or 'Original Prusa SL1S SPEED'}\n") # Example name
                # SLA specific details if needed
                f.write("supports_enable = 1\n") # Generally needed for SLA
                f.write("support_auto = 1\n")
            elif technology == Print3DTechnology.SLS:
                 f.write("printer_technology = SLS\n")
                 # SLS profiles (example - adjust as needed)
                 f.write(f"print_settings_id = {print_profile_name or f'{layer_height:.2f}mm QUALITY @SLS1'}\n") # Hypothetical
                 f.write(f"filament_settings_id = {material_profile_name or 'Generic PA12'}\n") # Use filament for material profile
                 f.write(f"printer_model = {printer_model or 'Prusa SLS1'}\n") # Hypothetical model
                 # SLS doesn't use traditional supports
                 f.write("supports_enable = 0\n")
            else: # FDM as default
                f.write("printer_technology = FFF\n")
                # Use generic FDM profiles if specific ones aren't provided
                f.write(f"print_settings_id = {print_profile_name or f'{layer_height:.2f}mm QUALITY @MK3'}\n") # Example name
                f.write(f"filament_settings_id = {material_profile_name or 'Generic PLA'}\n") # Example name
                f.write(f"printer_model = {printer_model or 'Original Prusa i3 MK3'}\n") # Example name
                # Support settings for FDM (can be overridden)
                f.write("supports_enable = 1\n") # Enable supports by default for quoting
                f.write("support_material_buildplate_only = 1\n") # Common default
                f.write("support_threshold = 45\n") # Standard overhang angle

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
            "--export-gcode", # Force gcode export to get comments
            "--output", gcode_output_path,
            stl_file_path
        ]

        logger.info(f"Running slicer command: {' '.join(cmd)}")
        slicer_start_time = time.time()

        try:
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

            # Check if G-code file was created
            if not os.path.exists(gcode_output_path) or os.path.getsize(gcode_output_path) == 0:
                 # Sometimes slicer exits 0 but fails to write output (e.g. if model is invalid)
                 error_message = f"Slicer ran successfully (code 0) but did not produce G-code output file: {gcode_output_path}"
                 if process.stderr: # Include stderr for clues
                      error_message += f"\nSlicer Output (stderr):\n{process.stderr[:1000]}..."
                 raise SlicerError(error_message)

            # Read the G-code file content
            with open(gcode_output_path, "r") as f:
                gcode_content = f.read()

            # Parse the G-code for estimates
            print_time_sec, filament_mm3, filament_g = _parse_gcode_estimates(gcode_content)

            # Validate parsed results - essential estimates must be present
            if print_time_sec is None or filament_mm3 is None:
                 error_msg = "Failed to parse critical time or volume estimates from slicer G-code output."
                 logger.error(error_msg)
                 # Include G-code snippet in error potentially
                 gcode_end_snippet = gcode_content[-2000:] # Last ~2KB usually has comments
                 logger.debug(f"G-code end snippet for parsing failure:\n{gcode_end_snippet}")
                 raise SlicerError(error_msg)

            # If weight (g) wasn't parsed directly, calculate it from volume and density
            if filament_g is None:
                 if material_density_g_cm3 is None or material_density_g_cm3 <= 0:
                      raise ConfigurationError("Material density must be provided and positive if slicer does not report weight.")
                 # Convert mm3 to cm3 for density calculation
                 filament_cm3 = filament_mm3 / 1000.0
                 filament_g = filament_cm3 * material_density_g_cm3
                 logger.info(f"Calculated filament weight from volume: {filament_cm3:.2f} cm3 * {material_density_g_cm3} g/cm3 = {filament_g:.2f} g") # Changed level to info


            # Placeholder for warnings from slicer output (if needed)
            slicer_warnings = []
            # Example: could parse process.stderr for lines starting with "Warning:"

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
# main_cli.py

import typer
from pathlib import Path
import logging
import sys
import json
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.pretty import pretty_repr
import argparse
import time
import os

# Project specific imports
# Need to adjust path if running as script vs installed module
try:
     # from config import settings # Import the loaded settings instance
     from quote_system.config import settings # Import the loaded settings instance
     # from core.common_types import ManufacturingProcess, QuoteResult, DFMIssue, DFMStatus, DFMLevel
     from quote_system.core.common_types import ManufacturingProcess, QuoteResult, DFMIssue, DFMStatus, DFMLevel
     # from core.exceptions import ManufacturingQuoteError
     from quote_system.core.exceptions import ManufacturingQuoteError
     # Import Processors
     # from processes.print_3d.processor import Print3DProcessor
     from quote_system.processes.print_3d.processor import Print3DProcessor
     # from processes.cnc.processor import CncProcessor
     from quote_system.processes.cnc.processor import CncProcessor
     # from visualization.viewer import show_model_with_issues # Import when viewer is ready
     from quote_system.visualization.viewer import show_model_with_issues # Import when viewer is ready
except ImportError:
     print("Error: Could not import project modules. Make sure you are running from the project root or have installed the package.")
     # Add project root to path temporarily for direct script execution
     # This assumes main_cli.py is in backend/quote_system
     project_root = Path(__file__).parent.parent.parent.resolve()
     # We SHOULD NOT need this sys.path hack if absolute imports from the root are used
     # and the code is run as a module or the root is in PYTHONPATH.
     # quote_system_root = Path(__file__).parent.resolve()
     # if str(quote_system_root) not in sys.path:
     #      sys.path.insert(0, str(quote_system_root))
     # Re-attempting imports here is usually a sign of problematic structure.
     # If the first try fails, fixing sys.path might work but it's better to fix the root cause.
     # We'll leave the original fallback structure but comment out the sys.path modification
     # and print a more informative error if it still fails.
     try:
          from quote_system.config import settings
          from quote_system.core.common_types import ManufacturingProcess, QuoteResult, DFMIssue, DFMStatus, DFMLevel
          from quote_system.core.exceptions import ManufacturingQuoteError
          from quote_system.processes.print_3d.processor import Print3DProcessor
          from quote_system.processes.cnc.processor import CncProcessor
          from quote_system.visualization.viewer import show_model_with_issues
     except ImportError as e:
          print(f"Failed to import project modules even after path adjustment attempt: {e}")
          print("Ensure 'backend' directory is in your PYTHONPATH or run commands as modules from the project root (e.g., python -m quote_system.main_cli ...)")
          sys.exit(1)

# Initialize logging
from config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# --- Typer App Initialization ---
app = typer.Typer(help="DFM Analysis and Instant Quoting CLI Tool")
console = Console()

# --- Processor Initialization (similar to API) ---
# This might duplicate initialization if API also runs, consider refactoring later
PROCESSORS_CLI: Dict[ManufacturingProcess, Any] = {}
try:
    PROCESSORS_CLI[ManufacturingProcess.PRINT_3D] = Print3DProcessor(markup=settings.markup_factor)
    PROCESSORS_CLI[ManufacturingProcess.CNC] = CncProcessor(markup=settings.markup_factor)
    # Add SheetMetal when ready
except Exception as e:
    logger.error(f"CLI failed to initialize processors: {e}")
    # Allow CLI to run for listing materials etc, but quoting might fail

def get_processor_cli(process: ManufacturingProcess, markup_override: Optional[float] = None):
    """Gets or initializes processor with optional markup override for CLI."""
    markup = markup_override if markup_override is not None else settings.markup_factor
    if markup < 1.0:
        console.print("[bold red]Error: Markup must be >= 1.0[/]")
        raise typer.Exit(code=1)

    # If processor already initialized with correct markup, return it
    if process in PROCESSORS_CLI and PROCESSORS_CLI[process].markup == markup:
        return PROCESSORS_CLI[process]

    # Otherwise, initialize a new one for the CLI context if needed, or re-init the shared one
    # For simplicity here, we just re-initialize the shared instance if markup differs
    # This assumes processor init is lightweight.
    logger.info(f"Initializing {process.value} processor for CLI with markup={markup:.2f}")
    try:
        if process == ManufacturingProcess.PRINT_3D:
            PROCESSORS_CLI[process] = Print3DProcessor(markup=markup)
        elif process == ManufacturingProcess.CNC:
            PROCESSORS_CLI[process] = CncProcessor(markup=markup)
        # Add SheetMetal
        else:
             raise NotImplementedError(f"CLI does not support processor for {process.value}")
        return PROCESSORS_CLI[process]
    except Exception as e:
        console.print(f"[bold red]Error initializing processor for {process.value}: {e}[/]")
        raise typer.Exit(code=1)


# --- CLI Commands ---

@app.command()
def list_materials(
    process: ManufacturingProcess = typer.Argument(..., help="Manufacturing process (e.g., '3D Printing', 'CNC Machining')")
):
    """Lists available materials for the specified manufacturing process."""
    try:
        processor = get_processor_cli(process)
        materials = processor.list_available_materials()

        if not materials:
            console.print(f"[yellow]No materials found for {process.value}.[/]")
            return

        table = Table(title=f"Available Materials for {process.value}", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=20)
        table.add_column("Name")
        table.add_column("Technology", width=15)
        table.add_column("Density (g/cm³)", justify="right")
        table.add_column("Cost", justify="right")

        for mat in materials:
            cost_str = "N/A"
            if mat.get("cost_per_kg") is not None:
                cost_str = f"${mat['cost_per_kg']:.2f}/kg"
            elif mat.get("cost_per_liter") is not None:
                 cost_str = f"${mat['cost_per_liter']:.2f}/L"

            table.add_row(
                mat.get("id", "N/A"),
                mat.get("name", "N/A"),
                str(mat.get("technology", "N/A")),
                f"{mat.get('density_g_cm3', 0):.3f}",
                cost_str
            )

        console.print(table)

    except ManufacturingQuoteError as e:
        console.print(f"[bold red]Error listing materials: {e}[/]")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.exception("Unexpected error listing materials:")
        console.print(f"[bold red]An unexpected error occurred: {e}[/]")
        raise typer.Exit(code=1)


@app.command()
def quote(
    file_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, help="Path to the 3D model file (.stl, .step, .stp)"),
    process: ManufacturingProcess = typer.Argument(..., help="Manufacturing process (e.g., '3D Printing', 'CNC Machining')"),
    material_id: str = typer.Argument(..., help="Material ID (use 'list-materials' command to see available IDs)"),
    markup: Optional[float] = typer.Option(None, "--markup", "-m", help="Override default markup factor (e.g., 1.6 for 60%). Must be >= 1.0."),
    output_json: Optional[Path] = typer.Option(None, "--output", "-o", help="Save the full quote result as a JSON file."),
    visualize: bool = typer.Option(False, "--visualize", "-v", help="Show 3D model visualization with DFM issues highlighted (requires GUI)."),
):
    """Analyzes a model file, performs DFM checks, and generates an instant quote."""
    console.print(f"Processing: [cyan]{file_path.name}[/]")
    console.print(f"Process: [cyan]{process.value}[/]")
    console.print(f"Material: [cyan]{material_id}[/]")
    if markup:
        console.print(f"Using custom markup: [yellow]{markup:.2f}[/]")

    try:
        processor = get_processor_cli(process, markup_override=markup)
        result: QuoteResult = processor.generate_quote(str(file_path), material_id)

        # --- Print Summary ---
        console.print(f"\n--- Quote Result (ID: {result.quote_id}) ---")
        console.print(f"Total Processing Time: {result.processing_time_sec:.3f} seconds")

        # DFM Report
        dfm_color = "green"
        if result.dfm_report.status == DFMStatus.WARNING: dfm_color = "yellow"
        elif result.dfm_report.status == DFMStatus.FAIL: dfm_color = "red"
        console.print(Panel(f"[bold {dfm_color}]{result.dfm_report.status.value}[/]"), title="DFM Status", expand=False)
        console.print(f"DFM Analysis Time: {result.dfm_report.analysis_time_sec:.3f} seconds")

        if result.dfm_report.issues:
            console.print("\n[bold]DFM Issues Found:[/]")
            for issue in result.dfm_report.issues:
                 level_color = "white"
                 if issue.level == DFMLevel.CRITICAL: level_color = "bold red"
                 elif issue.level == DFMLevel.ERROR: level_color = "red"
                 elif issue.level == DFMLevel.WARN: level_color = "yellow"
                 elif issue.level == DFMLevel.INFO: level_color = "blue"
                 console.print(f"- [{level_color}]{issue.level.value}[/] ({issue.issue_type.value}): {issue.message}")
                 if issue.recommendation:
                      console.print(f"  [dim]Recommendation:[/dim] {issue.recommendation}")
                 if issue.details:
                      console.print(f"  [dim]Details:[/dim] {pretty_repr(issue.details)}")

        # Costing (only if DFM didn't fail)
        if result.cost_estimate:
            console.print("\n[bold]Cost & Time Estimate:[/]")
            est = result.cost_estimate
            mat = result.material_info
            cost_table = Table(show_header=False, box=None, padding=(0, 1))
            cost_table.add_column()
            cost_table.add_column(justify="right")
            cost_table.add_row("Material:", f"{mat.name} ({mat.id})")
            cost_table.add_row("Part Volume:", f"{est.material_volume_cm3:.3f} cm³")
            if est.support_volume_cm3 is not None:
                 cost_table.add_row("Support Volume:", f"{est.support_volume_cm3:.3f} cm³")
            cost_table.add_row("Total Material Volume:", f"{est.total_volume_cm3:.3f} cm³")
            cost_table.add_row("Total Material Weight:", f"{est.material_weight_g:.2f} g")
            cost_table.add_row("Material Cost:", f"${est.material_cost:.2f}")
            cost_table.add_row("[bold]Base Cost (Material Only):[/]", f"[bold]${est.base_cost:.2f}[/]")
            cost_table.add_row(f"Markup (@{processor.markup:.2f}x):", f"${result.customer_price - est.base_cost:.2f}")
            cost_table.add_row("[bold green]Customer Price:[/]", f"[bold green]${result.customer_price:.2f}[/]")
            cost_table.add_row("Estimated Process Time:", f"{result.estimated_process_time_str}")
            cost_table.add_row("Cost Analysis Time:", f"{est.cost_analysis_time_sec:.3f} seconds")
            console.print(cost_table)
        elif result.dfm_report.status != DFMStatus.FAIL:
             console.print("[yellow]Cost estimation skipped due to non-critical DFM issues or other error.[/]")
        else:
              console.print("[red]Cost estimation skipped because DFM check failed.[/]")


        # --- Save JSON Output ---
        if output_json:
            try:
                # Ensure output directory exists relative to where CLI is run
                output_json.parent.mkdir(parents=True, exist_ok=True)
                # Use Pydantic's model_dump_json for proper serialization
                json_output = result.model_dump_json(indent=2)
                output_json.write_text(json_output)
                console.print(f"\n[green]Full quote result saved to: {output_json}[/]")
            except Exception as e:
                 console.print(f"\n[bold red]Error saving JSON output to {output_json}: {e}[/]")

        # --- Visualization ---
        if visualize:
            if result.dfm_report.status == DFMStatus.FAIL and not result.cost_estimate:
                 console.print("[yellow]Visualization might be limited as DFM failed early or mesh could not be fully processed.[/]")

            console.print("\n[blue]Attempting to launch 3D viewer...[/]")
            try:
                 # Need to reload the mesh as the processor doesn't store it
                 # Use absolute path potentially derived from input
                 abs_file_path = file_path.resolve()
                 # Use absolute import for geometry module
                 from quote_system.core import geometry
                 mesh_for_viz = geometry.load_mesh(str(abs_file_path))

                 # Dynamically import here to avoid hard dependency if GUI libs not installed
                 # Use absolute import for viewer
                 from quote_system.visualization.viewer import show_model_with_issues
                 show_model_with_issues(mesh_for_viz, result.dfm_report.issues)
                 console.print("[green]Viewer closed.[/]")
            except ImportError:
                 console.print("[bold red]Error: Could not import visualization libraries (PyVista, PyQt6/PySide6). Please ensure they are installed.[/]")
            except Exception as e:
                 logger.exception("Error launching visualization:")
                 console.print(f"[bold red]Error launching visualization: {e}[/]")

    except ManufacturingQuoteError as e:
        console.print(f"\n[bold red]Quote Generation Failed: {e}[/]")
        # Optionally print more context based on exception type
        raise typer.Exit(code=1)
    except Exception as e:
        logger.exception("Unexpected error during quote command:")
        console.print(f"\n[bold red]An unexpected error occurred: {e}[/]")
        raise typer.Exit(code=1)


# --- Main Execution ---
if __name__ == "__main__":
    app() 
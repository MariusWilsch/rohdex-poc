from typing import Dict, List, Tuple, Any, Callable, TypeVar, Optional
import pandas as pd
from datetime import datetime
from io import StringIO, BytesIO
from app.services.ai_service import AIService
from app.services.monitoring import system_monitor
from app.utils.retry_utils import execute_with_self_healing
from rich.console import Console
import json
import time
import functools

console = Console()
ai_service = AIService()


async def process_partie(content: bytes, filename: str = None) -> Dict:
    """
    Process Partie data from bytes content using AI with self-healing capabilities

    Note: There is a known issue with tare weights in some input files. The AI extraction
    correctly processes what's in the files, but client files sometimes contain incorrect
    tare weights. This is a data source issue, not an extraction issue.
    Last updated: 2024-02-24
    """
    start_time = time.time()
    operation = f"extract_partie_data:{filename or 'Unknown'}"

    try:
        # Convert bytes to string
        content_str = content.decode("utf-8")

        # Create metadata dict for monitoring
        metadata = {"filename": filename}

        # Execute with self-healing retry logic
        def extract():
            # Use AI to extract data synchronously
            result = ai_service.extract_partie_data(
                content_str, filename or "Unknown Partie"
            )
            return result

        result = execute_with_self_healing(
            operation_name=operation,
            extraction_func=extract,
        )

        # After successful execution, record additional metadata
        system_monitor.record_request(
            service="FileProcessor",
            operation=operation,
            success=True,
            duration=time.time() - start_time,
            metadata={"filename": filename, "bale_count": len(result["bales"])},
        )

        # Log results
        console.print(
            f"\n[bold green]Processed[/] [cyan]{len(result['bales'])}[/] [bold green]bales[/]"
        )
        console.print(
            f"[bold green]Total Gross:[/] [cyan]{result['totals']['gross_kg']:.2f}[/] [bold green]kg[/]"
        )
        console.print(
            f"[bold green]Total Net:[/] [cyan]{result['totals']['net_kg']:.2f}[/] [bold green]kg[/]"
        )
        console.print(
            f"[bold green]Total Net (lbs):[/] [cyan]{result['totals']['net_lbs']:.2f}[/] [bold green]lbs[/]"
        )

        return result
    except Exception as e:
        total_duration = time.time() - start_time
        error_msg = str(e)

        # Record fatal error
        system_monitor.record_error(
            service="FileProcessor",
            operation=operation,
            error_message=error_msg,
            metadata={"total_duration": total_duration},
        )

        console.print(
            f"[bold red]Error processing partie data:[/] {error_msg}", style="red"
        )
        raise ValueError(f"Error processing partie data: {error_msg}")


async def load_wahrheit(content: bytes) -> Tuple[Dict, str, str]:
    """
    Load Wahrheitsdatei mapping from bytes content using AI with self-healing capabilities

    Note: There is a known issue with tare weights in some input files. The AI extraction
    correctly processes what's in the files, but client files sometimes contain incorrect
    tare weights. This is a data source issue, not an extraction issue.
    Last updated: 2024-02-24
    """
    start_time = time.time()
    operation = "extract_wahrheit_data"

    console.print("\n[bold blue]=== Processing Wahrheitsdatei ===[/]")

    try:
        # Convert bytes to string
        content_str = content.decode("utf-8")

        # Execute with self-healing retry logic
        def extract():
            # Use AI to extract data synchronously
            result = ai_service.extract_wahrheit_data(content_str)
            return result

        # Execute with self-healing without passing metadata initially
        result = execute_with_self_healing(
            operation_name=operation,
            extraction_func=extract,
        )

        # After successful execution, record additional metadata
        system_monitor.record_request(
            service="FileProcessor",
            operation=operation,
            success=True,
            duration=time.time() - start_time,
            metadata={
                "product_count": len(result.get("product_map", {})),
                "container_no": result.get("container_no", "Unknown"),
            },
        )

        # Log results
        console.print("\n[bold green]Wahrheit Processing Results:[/]")
        console.print(
            f"[bold green]Container Number:[/] [cyan]{result['container_no']}[/]"
        )
        console.print(f"[bold green]Invoice Number:[/] [cyan]{result['invoice_no']}[/]")
        console.print("[bold green]Product Mappings:[/]")
        for partie, desc in result["product_map"].items():
            console.print(f"  [green]Partie {partie}:[/] [cyan]{desc}[/]")

        return result["product_map"], result["container_no"], result["invoice_no"]
    except Exception as e:
        total_duration = time.time() - start_time
        error_msg = str(e)

        # Record fatal error
        system_monitor.record_error(
            service="FileProcessor",
            operation=operation,
            error_message=error_msg,
            metadata={"total_duration": total_duration},
        )

        console.print(
            f"[bold red]Error processing wahrheit data:[/] {error_msg}", style="red"
        )
        raise ValueError(f"Error processing wahrheit data: {error_msg}")


def format_bales_data(bales: List[Dict]) -> str:
    """Format bales data according to template structure"""
    lines = []
    for bale in bales:
        line = f"{bale['bale_no']},{bale['gross_kg']:.2f} kg,{bale['tare_kg']:.2f} kg,{bale['net_kg']:.2f} kg,2.2046,{bale['net_lbs']:.2f}lbs"
        lines.append(line)
    return "\n".join(lines)


async def generate_packing_list(
    partie_contents: List, wahrheit_content: bytes, template_content: str
) -> str:
    """Generate packing list from partie, wahrheit and template files

    Args:
        partie_contents: List of objects with content and filename properties
        wahrheit_content: Bytes content of wahrheit file
        template_content: String content of template file

    Returns:
        String content of generated packing list
    """
    start_time = time.time()

    try:
        # Load Wahrheitsdatei using AI
        console.print("[bold blue]Processing Wahrheitsdatei...[/]")
        product_map, container_no, invoice_no = await load_wahrheit(wahrheit_content)

        # Find the start and end of the product section template
        start = template_content.find("{BEGIN_PRODUCT_SECTION}")
        end = template_content.find("{END_PRODUCT_SECTION}") + len(
            "{END_PRODUCT_SECTION}"
        )
        if start == -1 or end == -1:
            raise ValueError(
                "Template must contain {BEGIN_PRODUCT_SECTION} and {END_PRODUCT_SECTION} markers"
            )

        # Extract the product section template
        product_template = (
            template_content[start:end]
            .replace("{BEGIN_PRODUCT_SECTION}\n", "")
            .replace("\n{END_PRODUCT_SECTION}", "")
        )

        # Process all Partie contents
        product_sections = []
        console.print(
            f"\n[bold green]Processing[/] [cyan]{len(partie_contents)}[/] [bold green]Partie files:[/]"
        )
        for idx, partie_content in enumerate(partie_contents):
            # Extract partie number from filename (e.g., "Partie 33876.csv" -> "33876")
            partie_num = partie_content.filename.split()[1].split(".")[0]
            console.print(f"\n[bold green]Processing Partie[/] [cyan]{partie_num}[/]")
            product_data = await process_partie(
                partie_content.content, partie_content.filename
            )
            description = product_map.get(partie_num)
            console.print(
                f"[bold green]Found description from Wahrheit:[/] [cyan]{description}[/]"
            )
            section = generate_product_section(
                product_template, product_data, partie_num, product_map.get(partie_num)
            )
            product_sections.append(section)

        # Generate final document
        console.print("\n[bold green]Generating final document[/]")
        output_content = template_content[:start]  # Get header
        output_content = output_content.replace(
            "{INVOICE_NO}", invoice_no or datetime.now().strftime("%Y%m%d")
        )
        output_content = output_content.replace("{CONTAINER_NO}", container_no or "TBD")
        console.print(f"[bold green]Using Invoice No:[/] [cyan]{invoice_no}[/]")
        console.print(f"[bold green]Using Container No:[/] [cyan]{container_no}[/]")

        # Add all product sections
        output_content += "\n".join(product_sections)

        # Print cost summary if available
        if hasattr(ai_service, "cost_tracker") and ai_service.cost_tracker:
            ai_service.cost_tracker.print_summary()

        # Print monitoring summary
        system_monitor.print_summary()

        total_duration = time.time() - start_time

        # Record successful packing list generation
        system_monitor.record_request(
            service="PackingListGenerator",
            operation="generate_packing_list",
            success=True,
            duration=total_duration,
            metadata={
                "partie_count": len(partie_contents),
                "container_no": container_no,
                "invoice_no": invoice_no,
            },
        )

        return output_content

    except Exception as e:
        total_duration = time.time() - start_time
        error_msg = str(e)

        # Record fatal error
        system_monitor.record_error(
            service="PackingListGenerator",
            operation="generate_packing_list",
            error_message=error_msg,
            metadata={"total_duration": total_duration},
        )

        # Print monitoring summary even on error
        system_monitor.print_summary()

        raise e


def generate_product_section(
    template_section: str, product_data: Dict, partie_num: str, description: str
) -> str:
    """Generate a complete product section from template"""
    section = template_section.replace(
        "{PRODUCT_DESCRIPTION}", description or f"Unknown Product"
    )
    section = section.replace("{SAMPLE_NO}", partie_num)

    # Format and insert bales data
    bales_data = format_bales_data(product_data["bales"])
    section = section.replace("{BALES_DATA}", bales_data)

    # Insert totals
    totals = product_data["totals"]
    section = section.replace("{BALES_COUNT}", str(totals["bale_count"]))
    section = section.replace("{TOTAL_GROSS}", f"{totals['gross_kg']:.2f}")
    section = section.replace("{TOTAL_TARE}", f"{totals['tare_kg']:.2f}")
    section = section.replace("{TOTAL_NET}", f"{totals['net_kg']:.2f}")
    section = section.replace("{TOTAL_LBS}", f"{totals['net_lbs']:.2f}")
    section = section.replace("{TOTAL_GROSS_LBS}", f"{totals['gross_kg'] * 2.2046:.2f}")
    section = section.replace("{TOTAL_NET_LBS}", f"{totals['net_lbs']:.2f}")

    return section

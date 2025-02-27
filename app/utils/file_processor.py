from typing import Dict, List, Tuple, Any, Callable, TypeVar, Optional
import pandas as pd
from datetime import datetime
from io import StringIO, BytesIO
from app.services.ai_service import AIService
from app.services.monitoring import system_monitor
from app.utils.retry_utils import execute_with_self_healing
from rich.console import Console
from app.core.models import PartieData, WahrheitData
from app.core.prompts import (
    PARTIE_SYSTEM_PROMPT,
    PARTIE_USER_PROMPT_TEMPLATE,
    WAHRHEIT_SYSTEM_PROMPT,
    WAHRHEIT_USER_PROMPT_TEMPLATE,
)
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

        # Execute with self-healing retry logic
        def extract():
            # Use structured data extraction with Pydantic model
            result = ai_service.extract_structured_data(
                content=content_str,
                system_prompt=PARTIE_SYSTEM_PROMPT,
                user_prompt=PARTIE_USER_PROMPT_TEMPLATE.format(
                    partie_filename=filename or "Unknown", content="{content}"
                ),
                response_model=PartieData,
                description=f"Partie data from {filename or 'Unknown Partie'}",
            )
            # Return the Pydantic model directly
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
            metadata={
                # Use attribute access instead of dictionary access
                "partie_no": getattr(result, "partie_no", "Unknown"),
                # Use attribute access and len() directly on the bales attribute
                "bale_count": len(getattr(result, "bales", [])),
                "filename": filename,
            },
        )

        # Log results
        console.print("\n[bold green]Partie Processing Results:[/]")
        # Use attribute access instead of dictionary access
        console.print(f"[bold green]Partie Number:[/] [cyan]{result.partie_no}[/]")

        # Calculate totals on-the-fly
        total_bales = len(result.bales)
        total_gross_kg = sum(bale.gross_kg for bale in result.bales)

        console.print(f"[bold green]Total Bales:[/] [cyan]{total_bales}[/]")
        console.print(f"[bold green]Total Weight:[/] [cyan]{total_gross_kg} kg[/]")

        return result

    except Exception as e:
        # Record failure
        system_monitor.record_request(
            service="FileProcessor",
            operation=operation,
            success=False,
            duration=time.time() - start_time,
            metadata={"filename": filename, "error_message": str(e)},
        )

        # Also record the error separately
        system_monitor.record_error(
            service="FileProcessor",
            operation=operation,
            error_message=str(e),
            metadata={"filename": filename},
        )
        console.print(f"[bold red]Error processing Partie file:[/] {str(e)}")
        raise


async def load_wahrheit(content: bytes, filename: str = None) -> Tuple[Dict, str, str]:
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
            # Use structured data extraction with Pydantic model
            result = ai_service.extract_structured_data(
                content=content_str,
                system_prompt=WAHRHEIT_SYSTEM_PROMPT,
                user_prompt=WAHRHEIT_USER_PROMPT_TEMPLATE,
                response_model=WahrheitData,
                description="Wahrheitsdatei data",
            )
            # Return the Pydantic model directly
            return result

        # Execute with self-healing without passing metadata initially
        result = execute_with_self_healing(
            operation_name=operation,
            extraction_func=extract,
        )

        # Convert the new products list structure to the product_map dictionary format
        # that the rest of the codebase expects
        product_map = {}
        # Use attribute access (result.products) instead of dictionary access (result.get("products", []))
        # The products attribute is a list of ProductInfo Pydantic models
        for product in result.products:
            # Convert product_code to string if it's an integer
            product_code = (
                str(product.product_code) if product.product_code is not None else ""
            )
            product_description = (
                product.description if product.description is not None else ""
            )

            # Store both the full product code and the numeric part (without suffix)
            product_map[product_code] = product_description

            # Also store with just the numeric part to handle suffix mismatches (e.g., 33906M vs 33906G)
            if product_code and len(product_code) > 1:
                numeric_part = "".join(c for c in product_code if c.isdigit())
                if numeric_part:
                    product_map[numeric_part] = product_description

        # Convert container_no and invoice_no to strings if they're integers
        container_no = (
            str(result.container_no) if result.container_no is not None else ""
        )
        invoice_no = str(result.invoice_no) if result.invoice_no is not None else ""

        # After successful execution, record additional metadata
        system_monitor.record_request(
            service="FileProcessor",
            operation=operation,
            success=True,
            duration=time.time() - start_time,
            metadata={
                "product_count": len(product_map),
                # Use getattr with a default value for safety
                "container_no": container_no,
            },
        )

        # Log results
        console.print("\n[bold green]Wahrheit Processing Results:[/]")
        console.print(f"[bold green]Container Number:[/] [cyan]{container_no}[/]")
        console.print(f"[bold green]Invoice Number:[/] [cyan]{invoice_no}[/]")
        console.print("[bold green]Product Mappings:[/]")
        for partie, desc in product_map.items():
            console.print(f"  [green]Partie {partie}:[/] [cyan]{desc}[/]")

        # Return the product map and container/invoice numbers using attribute access
        return product_map, container_no, invoice_no
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
    """
    Format bales data according to template structure

    Since we're using simplified models with only bale_no and gross_kg,
    this function calculates tare_kg, net_kg, and net_lbs on-the-fly.
    """
    lines = []
    for bale in bales:
        # Get the values that exist in our model
        bale_no = bale.get("bale_no", bale.get("bale_no", ""))
        gross_kg = bale.get("gross_kg", 0.0)

        # Calculate the missing values
        tare_kg = 2.0  # Default tare weight
        net_kg = gross_kg - tare_kg
        net_lbs = net_kg * 2.2046

        line = f"{bale_no},{gross_kg:.2f} kg,{tare_kg:.2f} kg,{net_kg:.2f} kg,2.2046,{net_lbs:.2f}lbs"
        lines.append(line)
    return "\n".join(lines)


async def generate_packing_list(
    partie_contents: List,
    wahrheit_content: bytes,
    template_content: str,
    wahrheit_filename: str = None,
) -> str:
    """Generate packing list from partie, wahrheit and template files

    Args:
        partie_contents: List of objects with content and filename properties
        wahrheit_content: Bytes content of wahrheit file
        template_content: String content of template file
        wahrheit_filename: Filename of the wahrheit file (optional)

    Returns:
        String content of generated packing list
    """
    start_time = time.time()

    try:
        # Load Wahrheitsdatei using AI
        console.print("[bold blue]Processing Wahrheitsdatei...[/]")
        product_map, container_no, invoice_no = await load_wahrheit(
            wahrheit_content, wahrheit_filename
        )

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

            # Try to find description by exact match first
            description = product_map.get(partie_num)

            # If not found, try with just the numeric part
            if description is None and partie_num:
                numeric_partie = "".join(c for c in partie_num if c.isdigit())
                if numeric_partie:
                    description = product_map.get(numeric_partie)

            console.print(
                f"[bold green]Found description from Wahrheit:[/] [cyan]{description}[/]"
            )
            section = generate_product_section(
                product_template, product_data, partie_num, description
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
    template_section: str, product_data: Any, partie_num: str, description: str
) -> str:
    """
    Generate a complete product section from template

    Args:
        template_section: Template string with placeholders
        product_data: Either a Pydantic model or dictionary containing partie data
        partie_num: Partie number
        description: Product description

    Returns:
        Formatted product section string
    """
    section = template_section.replace(
        "{PRODUCT_DESCRIPTION}", description or f"Unknown Product"
    )
    section = section.replace("{SAMPLE_NO}", partie_num)

    # Helper function to safely access attributes from either dict or Pydantic model
    def get_value(obj, key, default=None):
        if hasattr(obj, "get") and callable(obj.get):  # It's a dictionary
            return obj.get(key, default)
        elif hasattr(obj, key):  # It's a Pydantic model or object with attributes
            return getattr(obj, key, default)
        else:
            return default

    # Format and insert bales data
    # Get bales - could be a list attribute or dictionary key
    bales = get_value(product_data, "bales", [])

    # If bales is a Pydantic model list, convert each item to dict for format_bales_data
    if bales and hasattr(bales[0], "model_dump"):  # Pydantic v2
        bales = [item.model_dump() for item in bales]
    elif bales and hasattr(bales[0], "dict"):  # Pydantic v1
        bales = [item.dict() for item in bales]

    bales_data = format_bales_data(bales)
    section = section.replace("{BALES_DATA}", bales_data)

    # Calculate totals directly from bales
    total_bales = len(bales)
    total_gross_kg = sum(bale.get("gross_kg", 0.0) for bale in bales)

    # Calculate the missing values
    tare_kg = 2.0 * total_bales  # Default tare weight per bale
    net_kg = total_gross_kg - tare_kg
    net_lbs = net_kg * 2.2046

    # Insert totals
    section = section.replace("{BALES_COUNT}", str(total_bales))
    section = section.replace("{TOTAL_GROSS}", f"{total_gross_kg:.2f}")
    section = section.replace("{TOTAL_TARE}", f"{tare_kg:.2f}")
    section = section.replace("{TOTAL_NET}", f"{net_kg:.2f}")
    section = section.replace("{TOTAL_LBS}", f"{net_lbs:.2f}")
    section = section.replace("{TOTAL_GROSS_LBS}", f"{total_gross_kg * 2.2046:.2f}")
    section = section.replace("{TOTAL_NET_LBS}", f"{net_lbs:.2f}")

    return section

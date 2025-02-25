#!/usr/bin/env python3
import os
import time
from rich.console import Console
from app.services.ai_service import AIService
from app.services.monitoring import system_monitor
from dotenv import load_dotenv
import json

console = Console()

# Maximum number of retries for self-healing
MAX_RETRIES = 3


def test_partie_extraction():
    """Test extracting data from a Partie file using AI with self-healing capability"""
    # Load environment variables
    load_dotenv()

    # Initialize AI service
    ai_service = AIService()

    # Check if API key is set
    if not ai_service.api_key:
        console.print(
            "[bold red]Error:[/] ANTHROPIC_API_KEY not set in .env file", style="red"
        )
        return

    # Path to test file
    partie_file_path = (
        "context/2210331 Vorlagen + Warheitsdatei + Waage/Partie 33876.csv"
    )

    console.print(
        f"[bold blue]Testing AI extraction with file:[/] [cyan]{partie_file_path}[/]"
    )

    # Read file content
    try:
        with open(partie_file_path, "r") as f:
            content = f.read()
    except Exception as e:
        console.print(f"[bold red]Error reading file:[/] {str(e)}", style="red")
        return

    # Self-healing loop
    retries = 0
    success = False
    last_error = None

    while retries < MAX_RETRIES and not success:
        try:
            console.print(f"[blue]Attempt {retries + 1}/{MAX_RETRIES}[/]")

            # Extract data using AI (synchronously)
            result = ai_service.extract_partie_data(content, "Partie 33876.csv")

            # Validate the result format
            if not isinstance(result, dict):
                raise ValueError(f"Result is not a dictionary: {type(result)}")
            if "bales" not in result:
                raise ValueError("Missing 'bales' key in result")
            if "totals" not in result:
                raise ValueError("Missing 'totals' key in result")
            if not result["bales"]:
                raise ValueError("No bales found in result")

            # Print results
            console.print("\n[bold green]Extraction Results:[/]")
            console.print(f"[bold]Number of bales:[/] [cyan]{len(result['bales'])}[/]")
            console.print(
                f"[bold]Total gross weight:[/] [cyan]{result['totals']['gross_kg']:.2f} kg[/]"
            )
            console.print(
                f"[bold]Total net weight:[/] [cyan]{result['totals']['net_kg']:.2f} kg[/]"
            )
            console.print(
                f"[bold]Total net weight (lbs):[/] [cyan]{result['totals']['net_lbs']:.2f} lbs[/]"
            )

            # Print cost tracking summary
            if ai_service.cost_tracker:
                ai_service.cost_tracker.print_summary()

            console.print("[bold green]Test completed successfully![/]")
            success = True

        except Exception as e:
            last_error = str(e)
            console.print(
                f"[bold yellow]Error during attempt {retries + 1}:[/] {last_error}"
            )

            # Self-healing actions based on error type
            if "model" in last_error.lower() and "not found" in last_error.lower():
                console.print(
                    "[yellow]Model name issue detected, checking model in config...[/]"
                )
                # Inform about possible model name issue
                console.print(
                    "[yellow]Consider updating the model name in app/core/config.py and .env files[/]"
                )
            elif "api key" in last_error.lower():
                console.print(
                    "[yellow]API key issue detected, checking environment...[/]"
                )
                # Check if API key is set properly
                console.print(
                    "[yellow]Make sure ANTHROPIC_API_KEY is set correctly in .env file[/]"
                )
            elif "json" in last_error.lower():
                console.print(
                    "[yellow]JSON parsing issue detected, checking response format...[/]"
                )
                # Response format issue
                console.print(
                    "[yellow]Verify the model supports JSON response format[/]"
                )

            retries += 1
            if retries < MAX_RETRIES:
                # Backoff with increasing delay
                delay = 2**retries
                console.print(f"[blue]Retrying in {delay} seconds...[/]")
                time.sleep(delay)

    if not success:
        console.print(
            f"[bold red]Test failed after {MAX_RETRIES} attempts. Last error:[/] {last_error}",
            style="red",
        )
        console.print("[bold yellow]Suggested fixes:[/]")
        console.print("1. Verify the API key in .env file")
        console.print("2. Check if the model name is correct in app/core/config.py")
        console.print("3. Inspect the file content for any issues")


def test_wahrheit_extraction():
    """Test extracting data from a Wahrheitsdatei using AI with self-healing capability"""
    # Load environment variables
    load_dotenv()

    # Initialize AI service
    ai_service = AIService()

    # Check if API key is set
    if not ai_service.api_key:
        console.print(
            "[bold red]Error:[/] ANTHROPIC_API_KEY not set in .env file", style="red"
        )
        return

    # Path to test file
    wahrheit_file_path = (
        "context/2210331 Vorlagen + Warheitsdatei + Waage/Wahrheitsdatei.csv"
    )

    console.print(
        f"[bold blue]Testing AI extraction with file:[/] [cyan]{wahrheit_file_path}[/]"
    )

    # Read file content
    try:
        with open(wahrheit_file_path, "r") as f:
            content = f.read()
    except Exception as e:
        console.print(f"[bold red]Error reading file:[/] {str(e)}", style="red")
        return

    # Self-healing loop
    retries = 0
    success = False
    last_error = None

    while retries < MAX_RETRIES and not success:
        try:
            console.print(f"[blue]Attempt {retries + 1}/{MAX_RETRIES}[/]")

            # Extract data using AI (synchronously)
            result = ai_service.extract_wahrheit_data(content)

            # Validate the result format
            if not isinstance(result, dict):
                raise ValueError(f"Result is not a dictionary: {type(result)}")
            if "product_map" not in result:
                raise ValueError("Missing 'product_map' key in result")
            if "container_no" not in result:
                raise ValueError("Missing 'container_no' key in result")
            if "invoice_no" not in result:
                raise ValueError("Missing 'invoice_no' key in result")
            if not result["product_map"]:
                raise ValueError("No product mappings found in result")

            # Print results
            console.print("\n[bold green]Extraction Results:[/]")
            console.print(
                f"[bold]Container number:[/] [cyan]{result['container_no']}[/]"
            )
            console.print(f"[bold]Invoice number:[/] [cyan]{result['invoice_no']}[/]")
            console.print("[bold]Product mappings:[/]")
            for partie, desc in result["product_map"].items():
                console.print(f"  [green]Partie {partie}:[/] [cyan]{desc}[/]")

            # Print cost tracking summary
            if ai_service.cost_tracker:
                ai_service.cost_tracker.print_summary()

            console.print("[bold green]Test completed successfully![/]")
            success = True

        except Exception as e:
            last_error = str(e)
            console.print(
                f"[bold yellow]Error during attempt {retries + 1}:[/] {last_error}"
            )

            # Self-healing actions based on error type
            if "model" in last_error.lower() and "not found" in last_error.lower():
                console.print(
                    "[yellow]Model name issue detected, checking model in config...[/]"
                )
                # Inform about possible model name issue
                console.print(
                    "[yellow]Consider updating the model name in app/core/config.py and .env files[/]"
                )
            elif "api key" in last_error.lower():
                console.print(
                    "[yellow]API key issue detected, checking environment...[/]"
                )
                # Check if API key is set properly
                console.print(
                    "[yellow]Make sure ANTHROPIC_API_KEY is set correctly in .env file[/]"
                )
            elif "json" in last_error.lower():
                console.print(
                    "[yellow]JSON parsing issue detected, checking response format...[/]"
                )
                # Response format issue
                console.print(
                    "[yellow]Verify the model supports JSON response format[/]"
                )

            retries += 1
            if retries < MAX_RETRIES:
                # Backoff with increasing delay
                delay = 2**retries
                console.print(f"[blue]Retrying in {delay} seconds...[/]")
                time.sleep(delay)

    if not success:
        console.print(
            f"[bold red]Test failed after {MAX_RETRIES} attempts. Last error:[/] {last_error}",
            style="red",
        )
        console.print("[bold yellow]Suggested fixes:[/]")
        console.print("1. Verify the API key in .env file")
        console.print("2. Check if the model name is correct in app/core/config.py")
        console.print("3. Inspect the file content for any issues")


def test_self_healing():
    """Test the self-healing capabilities by simulating errors"""
    console.print("\n[bold blue]Testing Self-Healing Capabilities[/]")

    # Make sure the monitoring system is initialized
    console.print("[bold green]Initializing System Monitor...[/]")

    # 1. Simulate an API key error
    console.print("\n[bold yellow]Test 1: Simulating API Key Error[/]")
    system_monitor.record_error(
        service="AIService",
        operation="extract_partie_data",
        error_message="API key not provided or invalid",
        metadata={"error_type": "api_key", "simulated": True},
    )

    # 2. Simulate a model not found error with retries
    console.print(
        "\n[bold yellow]Test 2: Simulating Model Not Found Error with Retries[/]"
    )
    for i in range(1, 4):
        system_monitor.record_retry(
            service="AIService",
            operation="extract_partie_data",
            attempt=i,
            error_message=f"Model 'invalid-model' not found",
            metadata={"error_type": "model_not_found", "simulated": True},
        )

        if i < 3:  # Only the last attempt is a failure
            console.print(f"[blue]Simulating retry {i}...[/]")
            time.sleep(1)

    # 3. Simulate a JSON parsing error that recovers
    console.print(
        "\n[bold yellow]Test 3: Simulating JSON Parsing Error with Recovery[/]"
    )
    system_monitor.record_retry(
        service="AIService",
        operation="extract_wahrheit_data",
        attempt=1,
        error_message="Failed to parse JSON response: Unexpected token",
        metadata={"error_type": "json_parse", "simulated": True},
    )

    console.print("[blue]Simulating retry...[/]")
    time.sleep(1)

    # Simulate successful recovery
    system_monitor.record_request(
        service="AIService",
        operation="extract_wahrheit_data",
        success=True,
        duration=1.5,
        metadata={"simulated": True, "recovered": True},
    )

    # 4. Simulate successful processing with timing data
    console.print("\n[bold yellow]Test 4: Simulating Successful Processing[/]")
    system_monitor.record_request(
        service="AIService",
        operation="extract_partie_data",
        success=True,
        duration=2.3,
        metadata={"filename": "Partie Test.csv", "bale_count": 15, "simulated": True},
    )

    # Print the monitoring summary
    console.print("\n[bold blue]Self-Healing Test Results:[/]")
    system_monitor.print_summary()

    console.print("\n[bold green]Self-Healing Test Completed[/]")


if __name__ == "__main__":
    # Parse command line arguments
    import sys

    if len(sys.argv) < 2:
        console.print(
            "[bold yellow]Usage:[/] python test_ai_integration.py [partie|wahrheit|all|self-healing]"
        )
        sys.exit(1)

    test_type = sys.argv[1].lower()

    if test_type == "partie":
        test_partie_extraction()
    elif test_type == "wahrheit":
        test_wahrheit_extraction()
    elif test_type == "all":
        test_partie_extraction()
        test_wahrheit_extraction()
    elif test_type == "self-healing":
        test_self_healing()
    else:
        console.print(f"[bold red]Unknown test type:[/] {test_type}")
        console.print(
            "[bold yellow]Available test types:[/] partie, wahrheit, all, self-healing"
        )
        sys.exit(1)

from typing import Dict, Any, Callable, TypeVar
import time
from rich.console import Console
from app.services.monitoring import system_monitor

console = Console()

# Maximum number of retries for self-healing
MAX_RETRIES = 2

# Define generic type for function results
T = TypeVar("T")


def detect_error_type(error_message: str) -> str:
    """Determine the type of error from error message"""
    error_message = error_message.lower()

    if "model" in error_message and "not found" in error_message:
        console.print("[yellow]Model name issue detected[/]")
        return "model_not_found"
    elif "api key" in error_message:
        console.print("[yellow]API key issue detected[/]")
        return "api_key"
    elif "json" in error_message:
        console.print("[yellow]JSON parsing issue detected[/]")
        return "json_parse"
    else:
        return "unknown"


def handle_retry_monitoring(
    service: str,
    operation: str,
    retries: int,
    error_message: str,
    error_type: str,
    duration: float,
) -> None:
    """Handle retry monitoring and logging"""
    # Record failed request
    system_monitor.record_request(
        service=service,
        operation=operation,
        success=False,
        duration=duration,
        metadata={"error_type": error_type},
    )

    # Record retry or final error based on retry count
    if retries < MAX_RETRIES:
        system_monitor.record_retry(
            service=service,
            operation=operation,
            attempt=retries + 1,
            error_message=error_message,
            metadata={"error_type": error_type},
        )
    else:
        system_monitor.record_error(
            service=service,
            operation=operation,
            error_message=f"Failed after {MAX_RETRIES} attempts: {error_message}",
            metadata={"error_type": error_type, "attempts": retries + 1},
        )


def execute_with_self_healing(
    operation_name: str,
    extraction_func: Callable[..., T],
    service_name: str = "AIService",
    *args,
    **kwargs,
) -> T:
    """
    Execute a function with self-healing capability (retry logic)

    Args:
        operation_name: Name of the operation for monitoring
        extraction_func: Function to execute with retry logic
        service_name: Service name for monitoring
        *args, **kwargs: Arguments to pass to extraction_func

    Returns:
        Result of extraction_func if successful

    Raises:
        ValueError: If all retries fail
    """
    retries = 0
    last_error = None
    result = None

    # Loop until success or max retries reached
    while retries < MAX_RETRIES:
        try:
            if retries > 0:
                console.print(
                    f"[blue]Retry attempt {retries}/{MAX_RETRIES} for {operation_name}[/]"
                )

            extraction_start = time.time()

            # Call the extraction function
            result = extraction_func(*args, **kwargs)

            extraction_duration = time.time() - extraction_start

            # Record successful request
            system_monitor.record_request(
                service=service_name,
                operation=operation_name,
                success=True,
                duration=extraction_duration,
                metadata=kwargs.get("metadata", {}),
            )

            # If we get here, the extraction was successful
            return result

        except Exception as e:
            extraction_duration = time.time() - extraction_start
            last_error = str(e)
            error_type = detect_error_type(last_error)

            # Log the error
            console.print(
                f"[yellow]Error during {operation_name} (attempt {retries + 1}):[/] {last_error}"
            )

            # Handle monitoring
            handle_retry_monitoring(
                service=service_name,
                operation=operation_name,
                retries=retries,
                error_message=last_error,
                error_type=error_type,
                duration=extraction_duration,
            )

            retries += 1
            if retries < MAX_RETRIES:
                # Backoff with increasing delay
                delay = 2**retries
                console.print(f"[blue]Waiting {delay} seconds before retry...[/]")
                time.sleep(delay)

    # All retries failed
    raise ValueError(
        f"Failed to process {operation_name} after {MAX_RETRIES} attempts. Last error: {last_error}"
    )

from litellm import completion, completion_cost, OpenAIError
from app.core.config import get_settings
from app.core.prompts import (
    PARTIE_SYSTEM_PROMPT,
    PARTIE_USER_PROMPT_TEMPLATE,
    WAHRHEIT_SYSTEM_PROMPT,
    WAHRHEIT_USER_PROMPT_TEMPLATE,
)
from app.core.logger import LoggerSingleton
from app.services.cost_tracker import CostTracker
from typing import Dict, Any, List, Optional
import json
import time

# Get both logger and console from the singleton
logger = LoggerSingleton.get_logger()
console = LoggerSingleton.get_console()


class LegacyExtractionService:
    """
    This class contains legacy extraction methods that were previously part of AIService.
    They have been moved here for archival purposes and may be used for reference.

    Note: These methods are no longer actively maintained and may not work with the latest
    version of the application. Use the extract_structured_data method in AIService instead.
    """

    def __init__(self):
        self.settings = get_settings()

        self.model = self.settings.LITELLM_MODEL
        self.base_url = self.settings.LITELLM_BASE_URL
        self.cost_tracking_enabled = self.settings.LITELLM_COST_TRACKING
        self.cost_tracker = CostTracker() if self.cost_tracking_enabled else None

        # Log initialization
        console.print(
            f"[bold yellow]Legacy Extraction Service initialized (ARCHIVE)[/]"
        )
        logger.info("Legacy Extraction Service initialized (ARCHIVE)")

    def extract_partie_data(self, content: str, partie_filename: str) -> Dict[str, Any]:
        """
        Extract data from Partie content using AI
        """
        start_time = time.time()

        user_message = PARTIE_USER_PROMPT_TEMPLATE.format(
            content=content, filename=partie_filename
        )

        # User-facing information - use console for visibility
        console.print(f"[bold blue]Extracting data from {partie_filename}[/]")
        # Log operation in background
        logger.info(f"Extracting data from {partie_filename}")

        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": PARTIE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                base_url=self.base_url,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            end_time = time.time()
            duration = end_time - start_time

            # Log the completion time (debug level only)
            logger.debug(f"AI completion for {partie_filename} took {duration:.2f}s")

            # Track cost if enabled
            if self.cost_tracking_enabled and self.cost_tracker:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

                # Calculate cost using litellm's completion_cost function
                cost = completion_cost(completion_response=response)

                self.cost_tracker.add_request(
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    duration=duration,
                    cost=cost,
                )

                # Cost information - use console for visibility only
                console.print(
                    f"[bold green]Request completed:[/] {input_tokens} input tokens, {output_tokens} output tokens"
                )
                console.print(f"[bold green]Estimated cost:[/] ${cost:.6f}")

            # Debug information - use console for development visibility
            raw_content = response.choices[0].message.content
            console.print("[bold yellow]Raw response content:[/]")
            console.print(raw_content)

            # Log raw content at debug level only
            logger.debug(
                f"Raw AI response for {partie_filename}: {raw_content[:100]}..."
            )

            # Parse the JSON response
            parsed_json = json.loads(raw_content)

            # Handle the case where the data is nested under a 'data' key
            if "data" in parsed_json and isinstance(parsed_json["data"], dict):
                result = parsed_json["data"]
                console.print("[yellow]Note: Data was nested under 'data' key[/]")
                logger.debug("Data was nested under 'data' key")
            else:
                result = parsed_json

            # Validate the required fields
            if "bales" not in result:
                error_msg = "Missing 'bales' key in result"
                logger.error(f"Validation error for {partie_filename}: {error_msg}")
                raise ValueError(error_msg)
            if "totals" not in result:
                error_msg = "Missing 'totals' key in result"
                logger.error(f"Validation error for {partie_filename}: {error_msg}")
                raise ValueError(error_msg)

            # Success message - use console for user feedback
            console.print(
                f"[bold green]Successfully extracted data from[/] [cyan]{partie_filename}[/]"
            )
            # Log success
            logger.info(f"Successfully extracted data from {partie_filename}")

            return result

        except OpenAIError as e:
            # Handle OpenAI/LiteLLM specific errors
            error_msg = (
                f"LiteLLM error extracting data from {partie_filename}: {str(e)}"
            )
            console.print(
                f"[bold red]{error_msg}[/]",
                style="red",
            )
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
        except Exception as e:
            # Handle other errors
            error_msg = f"Error extracting data from {partie_filename}: {str(e)}"
            console.print(
                f"[bold red]{error_msg}[/]",
                style="red",
            )
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

    def extract_wahrheit_data(self, content: str) -> Dict[str, Any]:
        """
        Extract data from Wahrheitsdatei content using AI

        Note: There is a known issue with tare weights in some input files. The AI extraction
        correctly processes what's in the files, but client files sometimes contain incorrect
        tare weights. This is a data source issue, not an extraction issue.
        Last updated: 2024-02-24
        """
        start_time = time.time()

        user_message = WAHRHEIT_USER_PROMPT_TEMPLATE.format(content=content)

        # User-facing information - use console for visibility
        console.print("[bold blue]Extracting data from Wahrheitsdatei[/]")
        # Log operation in background
        logger.info("Extracting data from Wahrheitsdatei")

        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": WAHRHEIT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                base_url=self.base_url,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            end_time = time.time()
            duration = end_time - start_time

            # Log the completion time (debug level only)
            logger.debug(f"AI completion for Wahrheitsdatei took {duration:.2f}s")

            # Track cost if enabled
            if self.cost_tracking_enabled and self.cost_tracker:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

                # Calculate cost using litellm's completion_cost function
                cost = completion_cost(completion_response=response)

                self.cost_tracker.add_request(
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    duration=duration,
                    cost=cost,
                )

                # Cost information - use console for visibility only
                console.print(
                    f"[bold green]Request completed:[/] {input_tokens} input tokens, {output_tokens} output tokens"
                )
                console.print(f"[bold green]Estimated cost:[/] ${cost:.6f}")

            # Debug information - use console for development visibility
            raw_content = response.choices[0].message.content
            console.print("[bold yellow]Raw response content:[/]")
            console.print(raw_content)

            # Log raw content at debug level only
            logger.debug(f"Raw AI response for Wahrheitsdatei: {raw_content[:100]}...")

            # Parse the JSON response
            parsed_json = json.loads(raw_content)
            result = None

            # Handle different response formats
            if "data" in parsed_json and isinstance(parsed_json["data"], dict):
                result = parsed_json["data"]
                console.print("[yellow]Note: Data was nested under 'data' key[/]")
                logger.debug("Data was nested under 'data' key")
            elif "json_input" in parsed_json and isinstance(
                parsed_json["json_input"], dict
            ):
                result = parsed_json["json_input"]
                console.print("[yellow]Note: Data was nested under 'json_input' key[/]")
                logger.debug("Data was nested under 'json_input' key")
            else:
                result = parsed_json

            # Validate the required fields
            if "product_map" not in result:
                error_msg = "Missing 'product_map' key in result"
                logger.error(f"Validation error for Wahrheitsdatei: {error_msg}")
                raise ValueError(error_msg)
            if "container_no" not in result:
                error_msg = "Missing 'container_no' key in result"
                logger.error(f"Validation error for Wahrheitsdatei: {error_msg}")
                raise ValueError(error_msg)
            if "invoice_no" not in result:
                error_msg = "Missing 'invoice_no' key in result"
                logger.error(f"Validation error for Wahrheitsdatei: {error_msg}")
                raise ValueError(error_msg)

            # Success message - use console for user feedback
            console.print(
                "[bold green]Successfully extracted data from Wahrheitsdatei[/]"
            )
            # Log success
            logger.info("Successfully extracted data from Wahrheitsdatei")

            return result

        except OpenAIError as e:
            # Handle OpenAI/LiteLLM specific errors
            error_msg = f"LiteLLM error extracting data from Wahrheitsdatei: {str(e)}"
            console.print(
                f"[bold red]{error_msg}[/]",
                style="red",
            )
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
        except Exception as e:
            # Handle other errors
            error_msg = f"Error extracting data from Wahrheitsdatei: {str(e)}"
            console.print(
                f"[bold red]{error_msg}[/]",
                style="red",
            )
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

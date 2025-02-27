from litellm import completion, completion_cost, OpenAIError
from app.core.config import get_settings
from app.core.logger import LoggerSingleton
from app.services.cost_tracker import CostTracker
from typing import Dict, Any, List, Optional, Type, TypeVar
from pydantic import BaseModel
import json, time, litellm


# Get both logger and console from the singleton
logger = LoggerSingleton.get_logger()
console = LoggerSingleton.get_console()

# Type variable for Pydantic model
T = TypeVar("T", bound=BaseModel)


class AIService:
    def __init__(self):
        self.settings = get_settings()
        # API keys are now set as environment variables in config.py

        self.model = self.settings.LITELLM_MODEL
        self.base_url = self.settings.LITELLM_BASE_URL
        self.cost_tracking_enabled = self.settings.LITELLM_COST_TRACKING
        self.cost_tracker = CostTracker() if self.cost_tracking_enabled else None

        # Log initialization with both console (for visibility) and logger (for records)
        console.print(
            f"[bold green]AI Service initialized with model:[/] [cyan]{self.model}[/]"
        )
        logger.info(f"AI Service initialized with model: {self.model}")

        # Check for missing API keys
        if not self.settings.ANTHROPIC_API_KEY and not self.settings.OPENAI_API_KEY:
            console.print(
                "[bold red]Warning:[/] No API keys provided. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env file.",
                style="red",
            )
            logger.warning(
                "No API keys provided. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env file."
            )

    def extract_structured_data(
        self,
        content: str,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        model: str = "gpt-4o",
        temperature: float = 0.1,
        description: str = "data",
    ) -> T:
        """
        Extract structured data using a Pydantic model for validation.
        This is the preferred method for extracting structured data.

        Args:
            content: The content to extract data from
            system_prompt: The system prompt to use
            user_prompt: The user prompt template (will be formatted with content)
            response_model: A Pydantic model class that defines the expected response structure
            model: The model to use (defaults to gpt-4o-mini)
            temperature: The temperature to use (defaults to 0.1)
            description: Description of what's being extracted (for logging)

        Returns:
            An instance of the provided Pydantic model
        """
        start_time = time.time()

        formatted_user_prompt = user_prompt.format(content=content)

        # User-facing information - use console for visibility
        console.print(
            f"[bold blue]Extracting {description} using structured output model:[/] [cyan]{model}[/]"
        )
        # Log operation in background
        logger.info(f"Extracting {description} using structured output model: {model}")

        litellm.enable_json_schema_validation = True

        console.print(formatted_user_prompt)

        try:
            response = completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": formatted_user_prompt},
                ],
                base_url=self.base_url,
                temperature=temperature,
                response_format=response_model,  # Use Pydantic model for structured output
                # temperature=0.2,
            )

            end_time = time.time()
            duration = end_time - start_time

            # Log the completion time (debug level only)
            logger.debug(f"AI completion for {description} took {duration:.2f}s")

            # Track cost if enabled
            if self.cost_tracking_enabled and self.cost_tracker:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

                # Calculate cost using litellm's completion_cost function
                cost = completion_cost(completion_response=response)

                self.cost_tracker.add_request(
                    model=model,
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

            console.print("Raw response for debugging:")
            console.print(response.choices[0])

            # Get the raw JSON string from the response
            json_string = response.choices[0].message.content

            # Parse the JSON string into a Python dictionary
            json_data = json.loads(json_string)

            # Validate the parsed JSON with the Pydantic model
            try:
                # Try Pydantic v2 method first
                parsed_result = response_model.model_validate(json_data)
            except AttributeError:
                console.print(
                    f"[bold red]Error validating JSON with Pydantic:[/] {str(e)}",
                    style="red",
                )
                logger.error(f"Error validating JSON with Pydantic: {str(e)}")
                console.print(f"JSON data: {json_data}")
                raise ValueError(f"Error validating JSON with Pydantic: {str(e)}")

            console.print(parsed_result)
            # Success message - use console for user feedback
            console.print(
                f"[bold green]Successfully extracted {description} with structured output[/]"
            )
            # Log success
            logger.info(f"Successfully extracted {description} with structured output")

            return parsed_result

        except OpenAIError as e:
            # Handle OpenAI/LiteLLM specific errors
            error_msg = f"LiteLLM error extracting {description}: {str(e)}"
            console.print(
                f"[bold red]{error_msg}[/]",
                style="red",
            )
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
        except Exception as e:
            # Handle other errors
            error_msg = f"Error extracting {description}: {str(e)}"
            console.print(
                f"[bold red]{error_msg}[/]",
                style="red",
            )
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

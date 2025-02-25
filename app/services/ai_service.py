from litellm import completion
from app.core.config import get_settings
from typing import Dict, Any, List, Optional
from rich.console import Console
import json
import time

console = Console()


class AIService:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = (
            self.settings.ANTHROPIC_API_KEY.get_secret_value()
            if self.settings.ANTHROPIC_API_KEY
            else None
        )
        self.model = self.settings.LITELLM_MODEL
        self.base_url = self.settings.LITELLM_BASE_URL
        self.cost_tracking_enabled = self.settings.LITELLM_COST_TRACKING
        self.cost_tracker = CostTracker() if self.cost_tracking_enabled else None

        console.print(
            f"[bold green]AI Service initialized with model:[/] [cyan]{self.model}[/]"
        )
        if not self.api_key:
            console.print(
                "[bold red]Warning:[/] No API key provided. Please set ANTHROPIC_API_KEY in .env file.",
                style="red",
            )

    def extract_partie_data(self, content: str, partie_filename: str) -> Dict[str, Any]:
        """Extract data from Partie file using AI"""
        start_time = time.time()

        system_prompt = """
        You are a data extraction assistant. Extract weight measurements from the provided CSV data.
        The data represents weight measurements from industrial scales.
        """

        user_prompt = f"""
        Extract the following information from this CSV data from file {partie_filename}:
        
        {content}
        
        For each row (representing a bale), extract:
        1. The gross weight (column K, index 10)
        2. Calculate net weight (gross - tare)
        3. Calculate net weight in lbs (net * 2.2046)
        
        Use a tare weight of 2.0 kg for all bales except the last one, which should use 1.6 kg.
        
        Return the data in JSON format with this structure:
        {{
            "bales": [
                {{
                    "bale_no": 1,
                    "gross_kg": 123.45,
                    "tare_kg": 2.0,
                    "net_kg": 121.45,
                    "net_lbs": 267.75
                }},
                // more bales...
            ],
            "totals": {{
                "gross_kg": 1234.56,
                "tare_kg": 20.0,
                "net_kg": 1214.56,
                "net_lbs": 2677.61,
                "bale_count": 10
            }}
        }}
        """

        console.print(
            f"[bold blue]Extracting data from Partie file:[/] [cyan]{partie_filename}[/]"
        )

        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                api_key=self.api_key,
                base_url=self.base_url,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            end_time = time.time()
            duration = end_time - start_time

            # Track cost if enabled
            if self.cost_tracking_enabled and self.cost_tracker:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                self.cost_tracker.add_request(
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    duration=duration,
                )
                console.print(
                    f"[bold green]Request completed:[/] {input_tokens} input tokens, {output_tokens} output tokens"
                )
                console.print(
                    f"[bold green]Estimated cost:[/] ${self.cost_tracker.calculate_cost(self.model, input_tokens, output_tokens):.6f}"
                )

            # Print raw response content for debugging
            raw_content = response.choices[0].message.content
            console.print("[bold yellow]Raw response content:[/]")
            console.print(raw_content)

            # Parse the JSON response
            parsed_json = json.loads(raw_content)

            # Handle the case where the data is nested under a 'data' key
            if "data" in parsed_json and isinstance(parsed_json["data"], dict):
                result = parsed_json["data"]
                console.print("[yellow]Note: Data was nested under 'data' key[/]")
            else:
                result = parsed_json

            # Validate the required fields
            if "bales" not in result:
                raise ValueError("Missing 'bales' key in result")
            if "totals" not in result:
                raise ValueError("Missing 'totals' key in result")

            console.print(
                f"[bold green]Successfully extracted data from[/] [cyan]{partie_filename}[/]"
            )
            return result

        except Exception as e:
            console.print(
                f"[bold red]Error extracting data from {partie_filename}:[/] {str(e)}",
                style="red",
            )
            raise ValueError(f"Error extracting data from {partie_filename}: {str(e)}")

    def extract_wahrheit_data(self, content: str) -> Dict[str, Any]:
        """
        Extract data from Wahrheitsdatei content using AI

        Note: There is a known issue with tare weights in some input files. The AI extraction
        correctly processes what's in the files, but client files sometimes contain incorrect
        tare weights. This is a data source issue, not an extraction issue.
        Last updated: 2024-02-24
        """
        start_time = time.time()

        system_message = """You are a helpful data extraction assistant. Your task is to extract structured data from CSV files used in the down/feather shipping industry.

Instructions for extracting data from Wahrheitsdatei (truth file):

INVOICE NUMBER - CRITICAL INSTRUCTIONS:
- DO NOT extract the invoice number from the first line that contains "V-LIEF#######"
- The CORRECT invoice number is a standalone 7-digit number that appears BELOW the main data table
- It typically appears a few empty lines after the last product entry
- Look for a line that ONLY contains a 7-digit number without any prefix or text around it

PRODUCT DESCRIPTION - CRITICAL INSTRUCTIONS:
- ONLY use the "Beschreibung 2" field for product descriptions, NOT the "Beschreibung" field
- "Beschreibung 2" contains the CAPITALIZED product names (e.g., "GRS RECYCLED GREY DOWN")
- "Beschreibung" contains lowercase descriptions with percentages (e.g., "GRS recycled grey down abt. 57%")
- You MUST extract ONLY the "Beschreibung 2" values for the product_map

Example layout showing proper field extraction:
```
V-LIEF2210332 Allied Feather & Down Corporation - Geb. Verkaufslieferung
Art  Nr.  Virtuelle Partie  Beschreibung                      Beschreibung 2            ...
Artikel  33906M  33906  GRS recycled grey down abt. 75%  GRS RECYCLED GREY DOWN     ...
Artikel  33876M  33876  GRS washed recycled grey down... GRS WASHED RECYCLED GREY DOWN...
[Several empty lines may appear here]
2210331    <--- THIS is the correct invoice number to extract (standalone number)
CAIU 427340-6
```

For the example above, your product map should be:
{
  "33906": "GRS RECYCLED GREY DOWN",
  "33876": "GRS WASHED RECYCLED GREY DOWN"
}

OTHER EXTRACTION INSTRUCTIONS:
1. Look for container information, typically in the format "CAIU ######-#" or similar
2. For each "Partie" (lot) number mentioned, extract its corresponding "Beschreibung 2" description
3. Return data in this format:
   {
     "container_no": "CONTAINER-NUMBER",
     "invoice_no": "INVOICE-NUMBER",
     "product_map": {
       "33906": "GRS RECYCLED GREY DOWN",
       "33876": "GRS WASHED RECYCLED GREY DOWN"
     }
   }

VALIDATION STEP:
Before returning your response, verify that:
1. The invoice number is a standalone 7-digit number that appears AFTER the product listings
2. Product descriptions in the product_map are ONLY from the "Beschreibung 2" column (capitalized descriptions)
3. You are NOT including any values from the "Beschreibung" column"""

        user_message = f"""Extract the structured data from this Wahrheitsdatei content, focusing on container number, invoice number, and product descriptions for each Partie number. 
Remember:
1. The invoice number is the standalone 7-digit number that appears BELOW the table
2. Use ONLY the "Beschreibung 2" column (CAPITALIZED descriptions) for the product map, NOT the "Beschreibung" column

```
{content}
```
        """

        console.print("[bold blue]Extracting data from Wahrheitsdatei[/]")

        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                api_key=self.api_key,
                base_url=self.base_url,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            end_time = time.time()
            duration = end_time - start_time

            # Track cost if enabled
            if self.cost_tracking_enabled and self.cost_tracker:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                self.cost_tracker.add_request(
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    duration=duration,
                )
                console.print(
                    f"[bold green]Request completed:[/] {input_tokens} input tokens, {output_tokens} output tokens"
                )
                console.print(
                    f"[bold green]Estimated cost:[/] ${self.cost_tracker.calculate_cost(self.model, input_tokens, output_tokens):.6f}"
                )

            # Print raw response content for debugging
            raw_content = response.choices[0].message.content
            console.print("[bold yellow]Raw response content:[/]")
            console.print(raw_content)

            # Parse the JSON response
            parsed_json = json.loads(raw_content)
            result = None

            # Handle different response formats
            if "data" in parsed_json and isinstance(parsed_json["data"], dict):
                result = parsed_json["data"]
                console.print("[yellow]Note: Data was nested under 'data' key[/]")
            elif "json_input" in parsed_json and isinstance(
                parsed_json["json_input"], dict
            ):
                result = parsed_json["json_input"]
                console.print("[yellow]Note: Data was nested under 'json_input' key[/]")
            else:
                result = parsed_json

            # Validate the required fields
            if "product_map" not in result:
                raise ValueError("Missing 'product_map' key in result")
            if "container_no" not in result:
                raise ValueError("Missing 'container_no' key in result")
            if "invoice_no" not in result:
                raise ValueError("Missing 'invoice_no' key in result")

            console.print(
                "[bold green]Successfully extracted data from Wahrheitsdatei[/]"
            )
            return result

        except Exception as e:
            console.print(
                f"[bold red]Error extracting data from Wahrheitsdatei:[/] {str(e)}",
                style="red",
            )
            raise ValueError(f"Error extracting data from Wahrheitsdatei: {str(e)}")


class CostTracker:
    """Tracks the cost of AI requests"""

    # Cost per 1M tokens (in USD) for different models
    COST_PER_MILLION_TOKENS = {
        "anthropic/claude-3-5-sonnet-20240620": {"input": 3.0, "output": 15.0},
        "anthropic/claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
        "anthropic/claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
        "openai/gpt-4o": {"input": 5.0, "output": 15.0},
        "openai/gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    }

    def __init__(self):
        self.requests = []
        self.total_cost = 0.0
        console.print("[bold green]Cost tracking enabled[/]")

    def add_request(
        self, model: str, input_tokens: int, output_tokens: int, duration: float
    ):
        """Add a request to the tracker"""
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        self.requests.append(
            {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "duration": duration,
                "timestamp": time.time(),
            }
        )
        self.total_cost += cost

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate the cost of a request"""
        if model not in self.COST_PER_MILLION_TOKENS:
            console.print(
                f"[bold yellow]Warning:[/] Unknown model {model}, using anthropic/claude-3-5-sonnet-20240620 pricing"
            )
            model = "anthropic/claude-3-5-sonnet-20240620"

        input_cost = (input_tokens / 1_000_000) * self.COST_PER_MILLION_TOKENS[model][
            "input"
        ]
        output_cost = (output_tokens / 1_000_000) * self.COST_PER_MILLION_TOKENS[model][
            "output"
        ]

        return input_cost + output_cost

    def get_total_cost(self) -> float:
        """Get the total cost of all requests"""
        return self.total_cost

    def get_request_count(self) -> int:
        """Get the number of requests made"""
        return len(self.requests)

    def get_token_usage(self) -> Dict[str, int]:
        """Get the total token usage"""
        input_tokens = sum(req["input_tokens"] for req in self.requests)
        output_tokens = sum(req["output_tokens"] for req in self.requests)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }

    def print_summary(self):
        """Print a summary of the cost tracking"""
        if not self.requests:
            console.print("[bold yellow]No requests tracked yet[/]")
            return

        token_usage = self.get_token_usage()
        console.print("\n[bold green]Cost Tracking Summary:[/]")
        console.print(f"Total requests: {self.get_request_count()}")
        console.print(f"Total input tokens: {token_usage['input_tokens']:,}")
        console.print(f"Total output tokens: {token_usage['output_tokens']:,}")
        console.print(f"Total tokens: {token_usage['total_tokens']:,}")
        console.print(f"Total cost: ${self.total_cost:.6f}")

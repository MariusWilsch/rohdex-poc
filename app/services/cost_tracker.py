from typing import Dict, Any, List
from app.core.logger import LoggerSingleton
import time

# Get both logger and console from the singleton
logger = LoggerSingleton.get_logger()
console = LoggerSingleton.get_console()


class CostTracker:
    """Tracks the cost of AI requests"""

    def __init__(self):
        self.requests = []
        self.total_cost = 0.0
        self.model_costs = {}
        # Use console for user-facing information
        console.print("[bold green]Cost tracking enabled[/]")
        # Log for system records
        logger.info("Cost tracking enabled")

    def add_request(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration: float,
        cost: float,
    ):
        """Add a request to the tracker"""
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

        # Track cost by model
        self.model_costs[model] = self.model_costs.get(model, 0.0) + cost

    def get_total_cost(self) -> float:
        """Get the total cost of all requests"""
        return self.total_cost

    def get_model_cost(self, model: str) -> float:
        """Get total cost for a specific model"""
        return self.model_costs.get(model, 0.0)

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

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get a summary of all costs"""
        token_usage = self.get_token_usage()
        return {
            "total_cost": self.total_cost,
            "model_costs": self.model_costs,
            "request_count": len(self.requests),
            "token_usage": token_usage,
            "last_request": self.requests[-1] if self.requests else None,
        }

    def print_summary(self):
        """Print a summary of the cost tracking"""
        if not self.requests:
            # Use console for user-facing message
            console.print("[bold yellow]No requests tracked yet[/]")
            # Log for system records
            logger.info("Cost tracking summary requested but no requests tracked yet")
            return

        token_usage = self.get_token_usage()

        # Summary information - use console for formatted display only
        console.print("\n[bold green]Cost Tracking Summary:[/]")
        console.print(f"Total requests: {self.get_request_count()}")
        console.print(f"Total input tokens: {token_usage['input_tokens']:,}")
        console.print(f"Total output tokens: {token_usage['output_tokens']:,}")
        console.print(f"Total tokens: {token_usage['total_tokens']:,}")
        console.print(f"Total cost: ${self.total_cost:.6f}")

        # Print cost by model
        if self.model_costs:
            console.print("\n[bold cyan]Cost by Model:[/]")
            for model, cost in self.model_costs.items():
                console.print(f"  {model}: ${cost:.6f}")

        # Log summary information once
        logger.info(
            f"Cost Tracking Summary: {self.get_request_count()} requests, "
            f"{token_usage['input_tokens']:,} input tokens, "
            f"{token_usage['output_tokens']:,} output tokens, "
            f"${self.total_cost:.6f} total cost"
        )

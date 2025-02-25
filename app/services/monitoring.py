from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
import time
from datetime import datetime
import threading
import json
import os
from pathlib import Path

console = Console()


class SystemMonitor:
    """Monitors the system health, error rates, and AI usage metrics"""

    def __init__(self, log_dir="logs"):
        self.start_time = time.time()
        self.requests = []
        self.errors = []
        self.retries = []
        self.log_dir = log_dir

        # Create log directory if it doesn't exist
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # Initialize log files
        self.log_file = os.path.join(
            log_dir, f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        console.print(
            f"[bold green]System Monitor initialized - logs will be saved to:[/] [cyan]{self.log_file}[/]"
        )

    def record_request(
        self,
        service: str,
        operation: str,
        success: bool,
        duration: float,
        metadata: Dict = None,
    ):
        """Record an API request"""
        request = {
            "timestamp": time.time(),
            "service": service,
            "operation": operation,
            "success": success,
            "duration": duration,
            "metadata": metadata or {},
        }
        self.requests.append(request)
        self._save_to_log("request", request)

    def record_error(
        self, service: str, operation: str, error_message: str, metadata: Dict = None
    ):
        """Record an error"""
        error = {
            "timestamp": time.time(),
            "service": service,
            "operation": operation,
            "error_message": error_message,
            "metadata": metadata or {},
        }
        self.errors.append(error)
        self._save_to_log("error", error)

    def record_retry(
        self,
        service: str,
        operation: str,
        attempt: int,
        error_message: str,
        metadata: Dict = None,
    ):
        """Record a retry attempt"""
        retry = {
            "timestamp": time.time(),
            "service": service,
            "operation": operation,
            "attempt": attempt,
            "error_message": error_message,
            "metadata": metadata or {},
        }
        self.retries.append(retry)
        self._save_to_log("retry", retry)

    def _save_to_log(self, event_type: str, data: Dict):
        """Save event to log file"""
        log_entry = {
            "type": event_type,
            "data": data,
            "system_uptime": time.time() - self.start_time,
        }

        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_error_rate(self) -> float:
        """Calculate the error rate"""
        if not self.requests:
            return 0.0
        successful_requests = sum(1 for req in self.requests if req["success"])
        return 1 - (successful_requests / len(self.requests))

    def get_retry_rate(self) -> float:
        """Calculate the retry rate"""
        if not self.requests:
            return 0.0
        return len(self.retries) / len(self.requests)

    def get_avg_response_time(self) -> float:
        """Calculate the average response time"""
        if not self.requests:
            return 0.0
        return sum(req["duration"] for req in self.requests) / len(self.requests)

    def get_service_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics by service"""
        services = {}

        for req in self.requests:
            service = req["service"]
            if service not in services:
                services[service] = {
                    "requests": 0,
                    "successful": 0,
                    "errors": 0,
                    "retries": 0,
                    "total_duration": 0.0,
                }

            services[service]["requests"] += 1
            if req["success"]:
                services[service]["successful"] += 1
            services[service]["total_duration"] += req["duration"]

        for error in self.errors:
            service = error["service"]
            if service in services:
                services[service]["errors"] += 1

        for retry in self.retries:
            service = retry["service"]
            if service in services:
                services[service]["retries"] += 1

        # Calculate averages
        for service, stats in services.items():
            if stats["requests"] > 0:
                stats["avg_duration"] = stats["total_duration"] / stats["requests"]
                stats["error_rate"] = 1 - (stats["successful"] / stats["requests"])
                stats["retry_rate"] = stats["retries"] / stats["requests"]
            else:
                stats["avg_duration"] = 0.0
                stats["error_rate"] = 0.0
                stats["retry_rate"] = 0.0

        return services

    def print_summary(self):
        """Print a summary of system monitoring"""
        console.print("\n[bold green]System Monitoring Summary:[/]")
        console.print(
            f"System uptime: {self._format_duration(time.time() - self.start_time)}"
        )
        console.print(f"Total requests: {len(self.requests)}")
        console.print(f"Error rate: {self.get_error_rate():.2%}")
        console.print(f"Retry rate: {self.get_retry_rate():.2%}")
        console.print(
            f"Average response time: {self.get_avg_response_time():.2f} seconds"
        )

        # Print service stats
        service_stats = self.get_service_stats()
        if service_stats:
            table = Table(title="Service Statistics")
            table.add_column("Service", style="cyan")
            table.add_column("Requests", justify="right")
            table.add_column("Success", justify="right")
            table.add_column("Errors", justify="right")
            table.add_column("Retries", justify="right")
            table.add_column("Error Rate", justify="right")
            table.add_column("Avg Time (s)", justify="right")

            for service, stats in service_stats.items():
                table.add_row(
                    service,
                    str(stats["requests"]),
                    str(stats["successful"]),
                    str(stats["errors"]),
                    str(stats["retries"]),
                    f"{stats['error_rate']:.2%}",
                    f"{stats['avg_duration']:.2f}",
                )

            console.print(table)

        # Recent errors
        if self.errors:
            console.print("\n[bold red]Recent Errors:[/]")
            for i, error in enumerate(reversed(self.errors[-5:])):
                console.print(
                    f"[red]{i+1}. {error['service']} - {error['operation']}: {error['error_message']}[/]"
                )

        # Recent retries
        if self.retries:
            console.print("\n[bold yellow]Recent Retries:[/]")
            for i, retry in enumerate(reversed(self.retries[-5:])):
                console.print(
                    f"[yellow]{i+1}. {retry['service']} - {retry['operation']} (Attempt {retry['attempt']}): {retry['error_message']}[/]"
                )

    def _format_duration(self, seconds: float) -> str:
        """Format duration in a human-readable format"""
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0 or days > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        return " ".join(parts)


# Global instance for easy access
system_monitor = SystemMonitor()

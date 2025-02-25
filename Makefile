.PHONY: run process-email setup clean

# Variables
PYTHON = python3
PORT = 8000

# Colors for output
GREEN = \033[0;32m
RED = \033[0;31m
NC = \033[0m # No Color

# Run the FastAPI server
run:
	@echo "$(GREEN)Starting FastAPI server on port $(PORT)...$(NC)"
	uvicorn app.main:app --reload --port $(PORT)

# Process emails with subject "Test - Rohdex"
process-email:
	@echo "$(GREEN)Processing Rohdex test emails...$(NC)"
	@curl -X POST "http://localhost:$(PORT)/api/v1/packing-list/process-email" \
		-H "Content-Type: application/json" \
		2>/dev/null || \
		(echo "$(RED)Failed to connect to server. Is it running? (make run)$(NC)" && exit 1)
	@echo "$(GREEN)Email processing request sent.$(NC)"

# Clean up generated files
clean:
	@echo "$(GREEN)Cleaning up...$(NC)"
	@rm -f generated_packing_list.csv
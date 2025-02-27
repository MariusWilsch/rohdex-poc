# Rohdex-POC

Rohdex Proof of Concept for processing packing lists using AI for data extraction.

## AI Integration with LiteLLM

This project uses LiteLLM to abstract away the complexity of different AI models. It supports Anthropic Claude models by default but can be configured to use others.

### Key Features

- **AI-powered extraction**: Extracts structured data from unstructured CSV files:
  - Partie files (weight measurements)
  - Wahrheitsdatei (product mappings and container information)
- **Cost tracking**: Monitors token usage and associated costs
- **Self-healing capabilities**: Implements retry mechanisms with exponential backoff for resilience against transient failures
- **Monitoring dashboard**: Provides real-time insights into system performance and error handling
- **Email processing**: Automatically processes emails with packing list attachments and sends back processed results

### Configuration

The AI integration is configured through environment variables:

```
# AI Configuration
ANTHROPIC_API_KEY=your-anthropic-api-key
LITELLM_MODEL=anthropic/claude-3-5-sonnet-20240620
LITELLM_BASE_URL=optional-proxy-url  # Only needed when using a proxy

# Email Configuration (for automatic email processing)
EMAIL_POLLING_ENABLED=true
EMAIL_POLL_INTERVAL=60
EMAIL_IMAP_SERVER=imap.example.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_SERVER=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-email@example.com
EMAIL_PASSWORD=your-email-password
```

### Components

1. **AIService** (`app/services/ai_service.py`)
   - Handles AI model interactions using LiteLLM
   - Extracts data from different file types
   - Tracks costs and token usage

2. **CostTracker** (`app/services/cost_tracker.py`)
   - Tracks token consumption and costs
   - Provides usage summaries and cost reporting

3. **Self-Healing Loop**
   - Implements intelligent retry strategies with exponential backoff
   - Helps recover from transient failures
   - Provides diagnostic information when issues occur

4. **System Monitor** (`app/services/monitoring.py`)
   - Tracks and logs all system operations
   - Records errors, retries, and success rates
   - Calculates performance metrics
   - Provides a web-based dashboard for monitoring

5. **PackingListService** (`app/services/packing_list_service.py`)
   - Processes partie and wahrheit files
   - Generates packing lists with structured data

6. **EmailService** (`app/services/email_service.py`)
   - Polls for new emails with attachments
   - Processes attachments using the AI service
   - Sends back processed results
   - Supports both IMAP and SMTP protocols

### Testing

Use the test_ai_integration.py script to test the AI extraction capabilities:

```bash
# Test Partie file extraction
python test_ai_integration.py partie

# Test Wahrheitsdatei extraction
python test_ai_integration.py wahrheit

# Test both
python test_ai_integration.py all

# Test self-healing capabilities
python test_ai_integration.py self-healing
```

### Response Format Handling

The integration handles various response formats from different AI models, including:
- Raw JSON responses
- Responses nested under a "data" key
- Responses nested under a "json_input" key

### Error Handling

The system includes comprehensive error handling with descriptive error messages to aid in troubleshooting issues with:
- API key validation
- Model availability
- JSON parsing
- Response validation

### Monitoring Dashboard

Once the application is running, access the monitoring dashboard at:

```
http://localhost:8000/api/v1/dashboard/monitoring
```

The dashboard provides:
- Real-time metrics on system health
- Service performance statistics
- Error and retry tracking
- Self-healing test capabilities

You can also access the raw metrics in JSON format at:

```
http://localhost:8000/api/v1/dashboard/metrics
```

This is useful for integrating with external monitoring tools.

### Email Processing

The system can automatically process emails with packing list attachments:

1. Monitors a specified email inbox for new messages
2. Extracts partie and wahrheit file attachments
3. Processes them using the AI service
4. Sends back the processed packing list
5. Marks processed emails as read

To enable email processing, configure the email settings in your `.env` file and ensure `EMAIL_POLLING_ENABLED=true`.

### Known Issues

- **Tare Weight Discrepancies**: There are known discrepancies in tare weights in some client input files. The AI extraction accurately processes what's in the files, but the source files occasionally contain incorrect tare weights (typically using 2.00 kg instead of the correct 4.00-4.40 kg values). This is a data source issue, not an extraction issue. (Last updated: 2024-02-24)

- **Invoice Number Precision**: The system has been improved to ensure accurate extraction of invoice numbers from Wahrheitsdatei files. If any discrepancies are found, please report them for further prompt optimization.

## Getting Started

1. Clone the repository
2. Install dependencies with Poetry: `poetry install`
3. Copy `.env.example` to `.env` and add your Anthropic API key and other configuration
4. Run tests to verify your setup: `python test_ai_integration.py all`
5. Start the application: `make run`
6. Access the monitoring dashboard at `http://localhost:8000/api/v1/dashboard/monitoring`

## License

[MIT](LICENSE) 
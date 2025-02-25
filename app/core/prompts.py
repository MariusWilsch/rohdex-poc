"""
Centralized storage for AI prompts used throughout the application.
This module contains system and user prompts for various AI extraction tasks.

Version History:
- v1.0.0 (2024-02-25): Initial creation with Partie and Wahrheit prompts
- v1.0.1 (2024-02-26): Updated PARTIE_USER_PROMPT_TEMPLATE to match Pydantic models
- v1.1 (2024-03-01): Simplified Partie prompt to focus on essential fields only
- v1.2 (2024-08-26): Removed totals from Partie prompt to simplify extraction
- v1.3 (2024-08-26): Updated WAHRHEIT_USER_PROMPT_TEMPLATE to use "Beschreibung 2" for product descriptions
- v1.4 (2024-08-26): Updated WAHRHEIT_USER_PROMPT_TEMPLATE to extract invoice number from above container number

HOW TO UPDATE THIS FILE:
1. When modifying existing prompts:
   - Update the version history with a new version number
   - Include a brief description of changes
   - Consider adding a comment above the modified prompt with the change details

2. When adding new prompts:
   - Use UPPERCASE for constant names
   - Add descriptive comments above each prompt
   - Group related prompts together
   - Update the version history

3. Prompt naming convention:
   - [TASK]_SYSTEM_PROMPT: For system prompts
   - [TASK]_USER_PROMPT_TEMPLATE: For user prompts with format placeholders
"""

# System prompts
WAHRHEIT_SYSTEM_PROMPT = """You are a specialized data extraction assistant for Rohdex GmbH.
Your task is to extract structured data from Wahrheitsdatei documents.
Provide your response as a valid JSON object matching the specified structure."""

PARTIE_SYSTEM_PROMPT = """You are a specialized data extraction assistant for Rohdex GmbH.
Your task is to extract structured data from Partie documents.
Provide your response as a valid JSON object matching the specified structure.
Extract only the raw data without performing any calculations."""

# User prompts
WAHRHEIT_USER_PROMPT_TEMPLATE = """Extract the key information from this Wahrheitsdatei document:

{content}

Important:
1. For product descriptions, always use "Beschreibung 2" field (e.g., "GRS RECYCLED GREY DOWN"), NOT "Beschreibung" field
2. If "Beschreibung 2" is not available, then use "Beschreibung" as a fallback
3. For the invoice number, use the number that appears ABOVE the container number (e.g., "2210331"), NOT the "V-LIEF" number at the top of the file

Ensure all required fields are included and formatted correctly."""

PARTIE_USER_PROMPT_TEMPLATE = """Extract the key information from this Partie file: {partie_filename}

{content}


Important:
1. Extract only the raw data without performing any calculations
2. The "bale_no" must be a string, not a number
3. Include all bales listed in the document
4. Ensure the "partie_no" is correctly extracted
5. Only extract the partie_no and bales with their gross weights

Ensure all required fields are included and formatted correctly.
"""

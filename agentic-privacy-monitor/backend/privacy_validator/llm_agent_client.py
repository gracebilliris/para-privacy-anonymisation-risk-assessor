"""
Generic LLM client for privacy monitoring agents.
Supports Gemini/Gemma models for column classification and privacy summary generation.
Used as an MCP tool for summarisation and column role inference.
"""

import os
import sys
import json
import re
from google import genai
from google.genai import types

def llm_generate_content(prompt: str, model: str) -> str:
    """
    Call the specified LLM API (Gemini/Gemma) with a prompt and return the generated text.
    Returns None on error.
    """
    try:
        client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
        )
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
        )
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        return response.text
    except Exception as e:
        print(f"LLM API error: {e}", file=sys.stderr)
        return None

def ask_llm_for_column_roles(headers: list[str], log_file_path: str = None) -> dict:
    """
    Use Gemma LLM to classify dataset headers into quasi-identifiers (QI) and sensitive attributes.
    Returns a dict with keys 'quasi_identifiers' and 'sensitive'.
    """

    def log_debug(msg):
        if log_file_path:
            try:
                with open(log_file_path, 'a') as f:
                    f.write(msg + '\n')
            except Exception:
                pass  # Silently ignore if log file can't be written
        # If no log_file_path, do nothing (no print to terminal)

    log_debug(f"[ask_llm_for_column_roles] headers: {headers}")
    prompt = (
        f"Given the following dataset columns: {headers}\n"
        "Which columns are likely quasi-identifiers (QIs) and which are sensitive attributes? "
        "Respond ONLY with a valid JSON object with keys 'quasi_identifiers' and 'sensitive'. "
        "Both values must be non-empty lists of valid column names from the input. "
        "If you are unsure, make your best guess, but never leave either list empty. "
        "Example: {\"quasi_identifiers\": [\"col1\"], \"sensitive\": [\"col2\"]}"
    )
    log_debug(f"[ask_llm_for_column_roles] prompt: {prompt}")

    response = llm_generate_content(prompt)
    log_debug(f"[ask_llm_for_column_roles] LLM response: {response}")
    qi = []
    sensitive = None
    if response:
        # Try to extract JSON from response text
        try:
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                qi = parsed.get("quasi_identifiers", [])
                sensitive = parsed.get("sensitive", None)
                # normalize sensitive if it comes as array
                if isinstance(sensitive, list) and sensitive:
                    sensitive = sensitive[0]
        except Exception as e:
            log_debug(f"Error parsing LLM response: {e}\nRaw response: {response}")

    # Fallback: if LLM returns empty, use heuristics
    if not qi and headers:
        qi = [headers[0]]
    if not sensitive and headers:
        sensitive = headers[-1]
    return {"quasi_identifiers": qi, "sensitive": sensitive}


def summarise_privacy_report(prompt_text: str, model: str) -> str:
    """
    Send a privacy summary prompt to the LLM and return a human-readable summary.
    Used by summariser agents as an MCP tool.
    """
    response = llm_generate_content(prompt_text, model)
    if not response:
        raise RuntimeError("LLM failed to generate summary")
    return response

if __name__ == "__main__":
    # CLI entry points for testing and scripting
    if len(sys.argv) >= 3 and sys.argv[1] == "--stdin":
        model = sys.argv[2]
        prompt_text = sys.stdin.read().strip()
        if not prompt_text:
            print("No prompt provided", file=sys.stderr)
            sys.exit(1)
        output = summarise_privacy_report(prompt_text, model)
        print(output)
    elif len(sys.argv) == 3:
        try:
            headers = json.loads(sys.argv[1])
            model = sys.argv[2]
        except Exception as e:
            print(json.dumps({"error": f"Invalid headers argument: {e}"}))
            sys.exit(1)
        result = ask_llm_for_column_roles(headers, model)
        print(json.dumps(result))
    else:
        print(json.dumps({"error": "Invalid arguments"}))
        sys.exit(1)

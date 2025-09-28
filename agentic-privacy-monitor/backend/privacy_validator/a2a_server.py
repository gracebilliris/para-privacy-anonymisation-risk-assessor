"""
A2A agent card endpoint and server for privacy monitoring agents.
Exposes /.well-known/agent.json and /a2a/message endpoints for agent-to-agent communication.
"""

import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from privacy_validator.adk_multi_agent_system import OrchestratorAgent

app = FastAPI()

# --- Agent Card ---
def get_agent_card():
    return {
        "capabilities": {"streaming": False},
        "defaultInputModes": ["text", "text/plain"],
        "defaultOutputModes": ["text", "text/plain"],
        "description": "Privacy monitoring agent system (validator, scanner, summariser)",
        "name": "privacy_monitor_agent",
        "protocolVersion": "0.2.6",
        "skills": [
            {"id": "validate_privacy", "name": "Privacy Validation", "description": "Checks anonymisation/privacy compliance", "tags": ["validation"]},
            {"id": "scan_privacy", "name": "Privacy Scanning", "description": "Scans for privacy risks", "tags": ["scanning"]},
            {"id": "summarise_privacy", "name": "Privacy Summarisation", "description": "Generates explanation reports", "tags": ["summarisation"]}
        ],
        "url": os.getenv("HOST_OVERRIDE", "http://localhost:8080/"),
        "version": "1.0.0"
    }

@app.get("/.well-known/agent.json")
def agent_card():
    return JSONResponse(get_agent_card())

# --- A2A Message Endpoint ---
@app.post("/a2a/message")
async def a2a_message(request: Request):
    data = await request.json()
    message = data.get("message", {})
    parts = message.get("parts", [])
    text = ""
    for part in parts:
        if part.get("type") == "text":
            text = part.get("text", "")
            break
    # Run orchestrator agent
    orchestrator = OrchestratorAgent()
    result = orchestrator.run(text)
    return JSONResponse({"result": result})

# --- Entrypoint ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

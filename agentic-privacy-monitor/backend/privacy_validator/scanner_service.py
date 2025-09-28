from fastapi import FastAPI, Request
from pydantic import BaseModel
from privacy_validator.adk_multi_agent_system import ScannerAgent

app = FastAPI()
agent = ScannerAgent()

class ScanRequest(BaseModel):
    dataset: str
    dataset_path: str = None

@app.get("/.well-known/agent.json")
def agent_card():
    return {
        "name": "scanner",
        "description": "Scans datasets for privacy risks.",
        "endpoint": "/scan",
        "skills": ["privacy_scan", "risk_assessment"]
    }

@app.post("/scan")
def scan(request: ScanRequest):
    result = agent.run(request.dataset, dataset_path=request.dataset_path)
    return result
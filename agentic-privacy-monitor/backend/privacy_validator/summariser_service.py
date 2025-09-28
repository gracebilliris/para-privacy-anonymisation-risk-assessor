from fastapi import FastAPI, Request
from pydantic import BaseModel
from privacy_validator.adk_multi_agent_system import SummariserAgent

app = FastAPI()
agent = SummariserAgent()

class SummariseRequest(BaseModel):
    datasets: list
    results: dict = None
    log_file_path: str = None

@app.get("/.well-known/agent.json")
def agent_card():
    return {
        "name": "summariser",
        "description": "Aggregates and summarises scan results.",
        "endpoint": "/summarise",
        "skills": ["summary", "aggregation"]
    }

@app.post("/summarise")
def summarise(request: SummariseRequest):
    validation_result = request.results.get("validation_result") if request.results else None
    scan_result = request.results.get("scan_result") if request.results else None
    log_file_path = request.log_file_path if hasattr(request, 'log_file_path') else None
    result = agent.run(
        validation_result,
        scan_result,
        dataset_names=request.datasets,
        log_file_path=log_file_path
    )
    return result
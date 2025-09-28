from fastapi import FastAPI
from pydantic import BaseModel
from privacy_validator.adk_multi_agent_system import ValidatorAgent

app = FastAPI()
agent = ValidatorAgent()

class ValidateRequest(BaseModel):
    dataset: str
    dataset_path: str = None

@app.get("/.well-known/agent.json")
def agent_card():
    return {
        "name": "validator",
        "description": "Checks anonymisation/privacy compliance.",
        "endpoint": "/validate",
        "skills": ["privacy_validation", "auxiliary_data_fetch"]
    }

@app.post("/validate")
def validate(request: ValidateRequest):
    try:
        result = agent.run(request.dataset, dataset_path=request.dataset_path)
        # Ensure the key exists and is a JSON string
        if not result or "validation_result" not in result:
            result = {"validation_result": {}}
        elif not isinstance(result["validation_result"], (str, dict)):
            result["validation_result"] = str(result["validation_result"])
    except Exception as e:
        # Fallback if validation fails
        result = {"validation_result": {}, "error": str(e)}
    return result

import os
import json
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional

from privacy_validator.adk_multi_agent_system import OrchestratorAgent, MultiDatasetSummariserAgent
from privacy_validator.summariser_agent import SummariserAgent

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate agents
agent = OrchestratorAgent()
multi_summariser_agent = MultiDatasetSummariserAgent()
summariser_agent = SummariserAgent()

class OrchestrateRequest(BaseModel):
    datasets: List[str]

@app.get("/privacymonitor/historical")
def get_historical_scans():
    results_dir = os.path.join(os.path.dirname(__file__), "../results")
    scan_folders = sorted(
        [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))],
        reverse=True
    )
    scans = []
    for folder in scan_folders:
        folder_path = os.path.join(results_dir, folder)
        scan_result_path = os.path.join(folder_path, "scan_results.json")
        explanation_path = os.path.join(folder_path, "explanation_report.txt")
        log_path = os.path.join(folder_path, "log.txt")

        scan = {"id": folder, "timestamp": folder}
        
        for key, path in [("results", scan_result_path), 
                          ("explanationReport", explanation_path), 
                          ("log", log_path)]:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        scan[key] = json.load(f) if key == "results" else f.read()
                except Exception:
                    scan[key] = None
        scans.append(scan)
    return JSONResponse(content={"scans": scans})

@app.get("/.well-known/agent.json")
def agent_card():
    return {
        "name": "orchestrator",
        "description": "Coordinates privacy scan workflow.",
        "endpoint": "/orchestrate",
        "skills": ["orchestration", "agent_discovery", "a2a_messaging"]
    }

@app.post("/orchestrate")
def orchestrate(request: OrchestrateRequest):
    results: List[Dict] = []
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%fZ")
    base_dir = os.path.join(os.path.dirname(__file__), "../results", timestamp)
    os.makedirs(base_dir, exist_ok=True)


    structured_explanations: List[Dict] = []

    import requests
    for dataset_path in request.datasets:
        dataset_name = os.path.basename(dataset_path)

        # Run orchestrator agent
        result = agent.run(dataset_path, dataset_path=dataset_path, log_dir=base_dir)

        # Safely parse MCP findings
        mcp_findings_raw = result.get("validation_result")
        mcp_findings: Dict = {}
        mcp_parse_error: Optional[str] = None
        debug_msg = f"[DEBUG {datetime.now()}] Raw MCP findings for {dataset_name}: {mcp_findings_raw}\n"

        if isinstance(mcp_findings_raw, dict):
            mcp_findings = mcp_findings_raw
        elif isinstance(mcp_findings_raw, str):
            try:
                mcp_findings = json.loads(mcp_findings_raw)
            except Exception as e:
                mcp_parse_error = f"Failed to parse MCP findings string: {str(e)}"
                debug_msg += f"[ERROR {datetime.now()}] {mcp_parse_error}\n"
        else:
            debug_msg += f"[WARN {datetime.now()}] MCP findings are None or unexpected type, defaulting to empty dict.\n"
        if not isinstance(mcp_findings, dict) or mcp_findings is None:
            debug_msg += f"[WARN {datetime.now()}] MCP findings was null or not a dict.\n"
        debug_msg += f"[DEBUG {datetime.now()}] MCP findings (pre-summary): {json.dumps(mcp_findings, default=str)}\n"

        # Append debug logs
        with open(os.path.join(base_dir, "log.txt"), "a") as logf:
            logf.write(debug_msg)

        # Use A2A: POST to /summarise endpoint for summary generation
        summarise_url = "http://localhost:8003/summarise"
        # Pass only the validator and scan results, not the full result dict
        summary_payload = {
            "datasets": [dataset_name],
            "results": {
                "validation_result": result.get("validation", {}),
                "scan_result": result.get("scan", {})
            },
            "log_file_path": os.path.join(base_dir, "log.txt")
        }
        # Log the exact payload being sent to the summariser
        debug_msg += f"[DEBUG {datetime.now()}] Payload to /summarise: {json.dumps(summary_payload, default=str)[:1000]}\n"
        try:
            resp = requests.post(summarise_url, json=summary_payload)
            debug_msg += f"[DEBUG {datetime.now()}] Response from /summarise: status={resp.status_code}, body={resp.text[:1000]}\n"
            if resp.status_code == 200:
                summary_text = resp.json().get("summary")
            else:
                summary_text = f"[ERROR] Summariser service returned status {resp.status_code}: {resp.text}"
        except Exception as e:
            summary_text = f"[ERROR] Failed to call summariser service: {e}"
            debug_msg += f"[ERROR {datetime.now()}] Exception calling /summarise: {e}\n"
        # Write updated debug log
        with open(os.path.join(base_dir, "log.txt"), "a") as logf:
            logf.write(debug_msg)

        explanation_file = os.path.join(base_dir, f"explanation_report_{dataset_name}.txt")
        try:
            with open(explanation_file, "w") as ef:
                ef.write(summary_text)
            structured_explanations.append({
                "dataset_name": dataset_name,
                "explanation": summary_text
            })
        except Exception:
            structured_explanations.append({
                "dataset_name": dataset_name,
                "explanation": None,
                "note": "Failed to save/read explanation"
            })

        results.append({
            "dataset": dataset_path,
            "result": result,
            "mcp_findings": mcp_findings,
            "mcp_findings_raw": mcp_findings_raw,
            "mcp_parse_error": mcp_parse_error
        })

    # Save combined results
    with open(os.path.join(base_dir, "scan_results.json"), "w") as f:
        json.dump({"results": results}, f, indent=2)

    # Read all individual summary files from disk for multi-dataset summary
    disk_explanations = []
    for dataset_path in request.datasets:
        dataset_name = os.path.basename(dataset_path)
        explanation_file = os.path.join(base_dir, f"explanation_report_{dataset_name}.txt")
        explanation_text = None
        try:
            with open(explanation_file, "r") as ef:
                explanation_text = ef.read()
        except Exception:
            explanation_text = None
        disk_explanations.append({
            "dataset_name": dataset_name,
            "explanation": explanation_text
        })
    # Generate combined summary using MultiDatasetSummariserAgent
    summary_result = multi_summariser_agent.run(
        disk_explanations,
        dataset_names=[os.path.basename(path) for path in request.datasets],
        log_file_path=os.path.join(base_dir, "log.txt")
    )
    summary_report = summary_result.get("summary") if isinstance(summary_result, dict) else str(summary_result)

    # Save combined summary report
    with open(os.path.join(base_dir, "explanation_report.txt"), "w") as f:
        f.write(summary_report)

    return {
        "results": results,
        "timestamp": timestamp,
        "explanation_report": summary_report
    }

def parse_validator_results(results: Dict) -> Dict:
    """Safely parse validator results and extract MCP findings."""
    mcp_findings: Dict = {}
    try:
        validation_result = results.get("validation_result", {})
        if isinstance(validation_result, str):
            validation_result = json.loads(validation_result)
        # Debug: print the structure and contents of validation_result
        import datetime
        try:
            with open('log.txt', 'a') as logf:
                logf.write(f"[DEBUG {datetime.datetime.now()}] validation_result: {json.dumps(validation_result, default=str)}\n")
        except Exception:
            pass
        if isinstance(validation_result, dict):
            params = validation_result.get("params", {})
            try:
                with open('log.txt', 'a') as logf:
                    logf.write(f"[DEBUG {datetime.datetime.now()}] params: {json.dumps(params, default=str)}\n")
            except Exception:
                pass
            qi_list = []
            sensitive_list = []
            if isinstance(params, dict):
                qi_list = params.get("qi", [])
                sensitive_list = params.get("sensitive", [])
            mcp_findings = {
                "k_anonymity": validation_result.get("k_anonymity"),
                "l_diversity": validation_result.get("l_diversity"),
                "t_closeness": validation_result.get("t_closeness"),
                "risk_flags": validation_result.get("risk_flags"),
                "repair_suggestions": validation_result.get("repair_suggestions"),
                "qi_list": qi_list,
                "sensitive": sensitive_list,
            }
    except (ValueError, TypeError) as e:
        print(f"[WARN] Failed to parse validation result: {e}")
        mcp_findings = {}
    return mcp_findings

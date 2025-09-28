"""
Entrypoint script to run OrchestratorAgent for a dataset and save results.
Usage: python run_orchestrator.py <dataset_path> <results_file> <summary_file>
"""
import sys
import os
import json
from privacy_validator.adk_multi_agent_system import SummariserAgent
from privacy_validator.adk_multi_agent_system import OrchestratorAgent

# Ensure backend directory is in sys.path for imports
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def main():
    if len(sys.argv) < 5:
        print("Usage: python run_orchestrator.py <dataset_path1> <dataset_path2> ... <results_file> <summary_file>", file=sys.stderr)
        sys.exit(1)
    # Last two args are results and summary files
    results_file = sys.argv[-2]
    summary_file = sys.argv[-1]
    dataset_paths = sys.argv[1:-2]
    orchestrator = OrchestratorAgent()
    all_results = []
    individual_scan_files = []
    individual_explanation_files = []
    log_dir = os.path.dirname(results_file)
    log_file = os.path.join(log_dir, "log.txt")
    def log_event(event: str):
        with open(log_file, "a") as lf:
            lf.write(event + "\n")
    # Collect validation and scan results for overview summary
    dataset_names = []
    validations = []
    scans = []
    for dataset_path in dataset_paths:
        with open(dataset_path, "r") as f:
            dataset = f.read()
        log_event(f"[START] Processing dataset: {dataset_path}")
        result = orchestrator.run(dataset, log_event=log_event, dataset_path=dataset_path)
        log_event(f"[END] Finished dataset: {dataset_path}")
        # Save individual scan result
        scan_file = dataset_path + ".scan.json"
        with open(scan_file, "w") as sf:
            json.dump(result, sf, indent=2)
        individual_scan_files.append(scan_file)
        # Save individual explanation
        explanation_file = dataset_path + ".explanation.txt"
        with open(explanation_file, "w") as ef:
            ef.write(result["summary"]["summary"])
        individual_explanation_files.append(explanation_file)
        all_results.append({"dataset": dataset_path, **result})
        dataset_names.append(os.path.basename(dataset_path))
        validations.append(result["validation"]["validation_result"])
        scans.append(result["scan"]["scan_result"])
    # Save all results
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)
    # Generate overview summary using SummariserAgent
    summariser = SummariserAgent()
    # Aggregate flags, recommendations, QIs, sensitive columns
    all_flags = []
    all_recommendations = []
    all_qis = set()
    all_sensitive = set()
    for v, s in zip(validations, scans):
        try:
            vj = json.loads(v)
        except Exception:
            vj = {"flags": [], "recommendations": []}
        try:
            sj = json.loads(s)
        except Exception:
            sj = {"quasi_identifiers": [], "sensitive": []}
        all_flags.extend(vj.get("flags", []))
        all_recommendations.extend(vj.get("recommendations", []))
        all_qis.update(sj.get("quasi_identifiers", []))
        sens = sj.get("sensitive", [])
        if isinstance(sens, list):
            all_sensitive.update(sens)
        elif sens:
            all_sensitive.add(sens)
    # Compose overview summary
    overview_summary = summariser.run(
        json.dumps({"flags": all_flags, "recommendations": all_recommendations}),
        json.dumps({"quasi_identifiers": list(all_qis), "sensitive": list(all_sensitive)}),
        dataset_names=dataset_names,
        log_event=log_event,
        dataset_path="ALL_DATASETS"
    )["summary"]
    # Save overview summary
    with open(summary_file, "w") as f:
        f.write(overview_summary)
    # Save index of individual files
    index_file = results_file.replace("scan_results.json", "scan_index.json")
    with open(index_file, "w") as idxf:
        json.dump({
            "scan_files": individual_scan_files,
            "explanation_files": individual_explanation_files
        }, idxf, indent=2)

if __name__ == "__main__":
    main()

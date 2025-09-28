# summariser_agent.py
"""
A summariser agent that uses an LLM to generate a concise summary of privacy reports.
"""
from typing import List, Dict
from .llm_agent_client import summarise_privacy_report
import json

class SummariserAgent:
    def extract_metrics(self, explanations: List[Dict]) -> List[Dict]:
        """
        Extract key privacy metrics from explanations to pass to the LLM.
        """
        extracted = []

        for i, explanation in enumerate(explanations):
            if isinstance(explanation, dict) and 'validation_result' in explanation:
                vr = explanation['validation_result']
                risk = vr.get('re_identification_risk')
                risk_label = "Low"
                if risk is not None:
                    risk_label = "High" if risk > 0.1 else "Low"
                else:
                    risk_label = "Unknown"

                metrics = {
                    "dataset_name": explanation.get("dataset_name", f"Dataset {i+1}"),
                    "re_identification_risk": risk if risk is not None else "N/A",
                    "risk_label": risk_label,
                    "k_anonymity": vr.get("k_anonymity", "Not calculated"),
                    "l_diversity": vr.get("l_diversity", "Not calculated"),
                    "t_closeness": vr.get("t_closeness", "Not calculated"),
                    "qi_cols": vr.get("qi_cols", []),
                    "sensitive_cols": vr.get("sensitive_cols", []),
                    "risk_flags": vr.get("risk_flags", []),
                    "repair_suggestions": vr.get("repair_suggestions", [])
                }
                extracted.append(metrics)
            else:
                extracted.append({
                    "dataset_name": f"Dataset {i+1}",
                    "re_identification_risk": "N/A",
                    "risk_label": "Unknown",
                    "k_anonymity": "Not calculated",
                    "l_diversity": "Not calculated",
                    "t_closeness": "Not calculated",
                    "qi_cols": [],
                    "sensitive_cols": [],
                    "risk_flags": [],
                    "repair_suggestions": [],
                    "note": "Explanation not structured properly."
                })
        return extracted

    def build_prompt(self, structured_metrics: List[Dict]) -> str:
        """
        Build a detailed prompt for the LLM using the raw metrics JSON.
        """
        prompt = (
            "You are a privacy-risk analysis assistant.\n\n"
            "Below is the raw output of a privacy scan of a dataset:\n"
            "RAW_SCAN_OUTPUT_JSON:\n"
            f"{json.dumps(structured_metrics, indent=2)}\n\n"
            "TASK:\n"
            "1. Privacy Assessment: Describe the overall privacy risk in clear, non-technical language. "
            "State whether re-identification risk is Low / Medium / High, and why.\n"
            "2. Key Metrics: Report k-anonymity, l-diversity, t-closeness, and re-identification risk. "
            "Compare them to thresholds if provided, and highlight any missing or failing metrics.\n"
            "3. Data Characteristics: List all quasi-identifier and sensitive columns, explaining why they could create privacy risk.\n"
            "4. Risk Flags: Summarize any risk flags or anomalies.\n"
            "5. Recommended Actions: Provide concrete mitigation steps (e.g., generalization, suppression, access controls), "
            "and recommend further analysis for missing metrics.\n\n"
            "FORMAT:\n"
            "Return a Markdown report with headings: Privacy Assessment, Key Metrics, Data Characteristics, Risk Flags, Recommended Actions."
        )
        return prompt

    def summarise(self, explanations: List[Dict]) -> str:
        """
        Generates a human-readable summary using the LLM.
        """
        if not explanations:
            return "No explanations provided."
        
        structured_metrics = self.extract_metrics(explanations)
        prompt = self.build_prompt(structured_metrics)

        try:
            summary = summarise_privacy_report(prompt, model="gemma-3n-e4b-it")
        except Exception as e:
            summary = f"LLM summarisation failed: {str(e)}"
        
        return summary

    def run(self, explanations, log_event=None, **kwargs):
        """
        Run summarisation and log debug output.
        """
        summary = self.summarise(explanations)
        import datetime
        debug_msg = f"[DEBUG {datetime.datetime.now()}] SummariserAgent summary output: {summary}\n"
        with open("log.txt", "a") as logf:
            logf.write(debug_msg)
        return summary

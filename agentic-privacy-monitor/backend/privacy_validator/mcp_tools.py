"""
MCP tool interface for privacy monitoring agents.
Provides standardized access to privacy validation, scanning, and summarization tools.
"""

from privacy_validator.llm_agent_client import ask_llm_for_column_roles, summarise_privacy_report
from privacy_validator.gemma_client import ask_llm_for_column_roles as gemma_column_roles, summarise_privacy_report as gemma_summarise
from privacy_validator.anonymisation_validator import AnonymisationValidator
import pandas as pd

class MCPPrivacyTools:
    """
    Model Context Protocol (MCP) tool interface for privacy monitoring.
    """
    def validate_privacy(self, dataset_path, model="gemini-pro"):
        df = pd.read_csv(dataset_path)
        headers = list(df.columns)
        # Use Gemini/Gemma to classify columns
        result = ask_llm_for_column_roles(headers, model)
        return result

    def scan_privacy(self, dataset_path, model="gemini-pro"):
        df = pd.read_csv(dataset_path)
        prompt = f"Scan the following dataset for privacy risks or sensitive information:\n{df.head().to_string()}"
        # Use Gemini/Gemma to scan
        summary = summarise_privacy_report(prompt, model)
        return summary

    def summarise_privacy(self, validation_result, scan_result, model="gemini-pro"):
        prompt = (
            f"Summarise the following privacy validation and scan results for a human reader.\n"
            f"Validation Result: {validation_result}\nScan Result: {scan_result}"
        )
        summary = summarise_privacy_report(prompt, model)
        return summary

    def full_report(self, dataset_path, qi_cols, sensitive_col, **kwargs):
        df = pd.read_csv(dataset_path)
        validator = AnonymisationValidator(df)
        report = validator.full_report(qi_cols=qi_cols, sensitive_col=sensitive_col, **kwargs)
        return report

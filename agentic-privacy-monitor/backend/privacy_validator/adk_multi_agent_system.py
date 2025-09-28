"""
ADK-based multi-agent system for privacy monitoring and privacy report summarisation.

Agents:
- ValidatorAgent: Checks anonymisation/privacy compliance using MCP (k-anonymity, l-diversity, t-closeness, etc.).
- ScannerAgent: Scans for privacy risks and classifies columns using LLM.
- SummariserAgent: Uses Gemma LLM as an MCP tool to generate a third-party, human-readable privacy summary for a single dataset.
- MultiDatasetSummariserAgent: Uses Gemma LLM as an MCP tool to generate a third-party, human-readable privacy summary for multiple datasets, including MCP findings and recommendations.
- OrchestratorAgent: Coordinates workflow between agents and aggregates results.

All summary generation is delegated to the LLM (Gemma) via gemma_client.summarise_privacy_report, ensuring output is clear, actionable, and suitable for non-technical audiences.
"""

from google.adk.agents import LlmAgent
from privacy_validator.gemma_client import ask_llm_for_column_roles
import json
from privacy_validator import gemma_client
from privacy_validator.mcp_tool_tabular_scanner import discover_tabular_datasets

# Multi-dataset summariser agent for orchestrator aggregation
class MultiDatasetSummariserAgent(LlmAgent):
    def __init__(self):
        super().__init__(
            name="multi_dataset_summariser",
            model="gemma-3n-e4b-it",
            description="Aggregates and summarises multiple dataset privacy reports into a single, LLM-generated summary."
        )
    def run(self, explanations, validator_results=None, dataset_names=None, log_event=None, log_file_path=None, **kwargs):
        """
        Generate a third-party privacy summary for multiple datasets using the Gemma LLM as an MCP tool.
        - Summarises privacy risks, recommendations, and MCP findings for each dataset.
        - Delegates summary construction to the LLM via gemma_client.summarise_privacy_report.
        - Truncates input to fit within LLM token limits.
        """
    
        # Helper to truncate text to a max number of characters (approx. 4 chars per token)
        def truncate(text, max_chars):
            if len(text) > max_chars:
                return text[:max_chars] + "... [truncated]"
            return text



        # Conservative estimate: 8192 tokens * 4 chars/token = 32,768 chars
        # Reserve 2,000 chars for instructions and formatting
        MAX_PROMPT_CHARS = 30000
        MAX_PER_DATASET = 2000  # chars per dataset block (validator + explanation)

        prompt = (
            "System: Data Privacy Impact Assessment & Reporting\n"
            "You are a third-party privacy auditor. Given the following datasets and their privacy scan results, generate a clear, actionable, and human-readable summary for a non-technical audience. For each dataset, include:\n"
            "- The dataset name (no file paths)\n"
            "- Any privacy risks or flags, with a brief explanation\n"
            "- Recommended actions (if any)\n"
            "- Model Context Protocol findings: k-anonymity, l-diversity, t-closeness, re-identification risk, and the threshold values used. IMPORTANT: Always report the actual metric values (even if low, zero, or below threshold). Do NOT say 'not calculated', 'not applicable', or 'not evaluated' unless the value is truly missing. If a metric is below threshold, state the value and that it did not meet the threshold.\n"
            "- An explicit risk level for each dataset (e.g., Low, Moderate, High), based on the findings\n"
            "For each dataset, include a section titled 'MCP Metric Findings' and present the following as a bullet list or table:\n"
            "  - k-anonymity: minimum, average, required threshold, and status (Met/Not met/Not applicable)\n"
            "  - l-diversity: minimum, average, method, required threshold, and status\n"
            "  - t-closeness: maximum, average, method, required threshold, and status\n"
            "  - re-identification risk: value, required threshold, and status\n"
            "Always include the actual values and thresholds for each metric, even if the metric is not met.\n\n"
            "Metric explanations (include these in the summary):\n"
            "- k-anonymity: Measures how well data can be disguised within a group. Low k-anonymity means individuals may be more easily re-identified.\n"
            "- l-diversity: Ensures that within each group, there is a sufficient number of distinct values for sensitive attributes. Low l-diversity means sensitive values are too similar within groups.\n"
            "- t-closeness: Measures how close the distribution of a sensitive attribute in a group is to the distribution in the overall dataset. High t-closeness indicates a higher risk of attribute disclosure.\n"
            "- Re-identification risk: Estimates the probability that an individual can be re-identified from the dataset, given the quasi-identifiers and sensitive attributes. A higher value means a greater risk of re-identification.\n"
            "Definitions for metric status (include these in the summary):\n"
            "- Not met: The metric was evaluated, but the dataset did not satisfy the required threshold (e.g., k-anonymity threshold was set, but the data did not reach it).\n"
            "- Not applicable: The metric does not apply to the dataset, often because of its structure, content, or the privacy configuration (e.g., t-closeness is only relevant for certain types of sensitive data).\n"
            "- Omitted: The metric was not calculated at all, either because the Model Context Protocol tool determined it was unnecessary, the dataset lacked the required attributes, or the scan configuration did not request it.\n\n"
            "At the end, provide a short overall assessment and next steps for ongoing privacy protection. Also, provide an explicit overall risk level (e.g., Low, Moderate, High) for all datasets combined, based on your findings.\n\n"
            "Datasets and results:\n"
        )

        used_chars = len(prompt)
        n_datasets = len(explanations)
        # Dynamically allocate per-dataset block size
        available_chars = MAX_PROMPT_CHARS - used_chars - 2000  # Reserve for summary instructions
        per_dataset_chars = max(1200, min(3000, available_chars // max(1, n_datasets)))
        for i, explanation in enumerate(explanations):
            if used_chars > MAX_PROMPT_CHARS:
                prompt += f"\n[Truncated: Too many datasets to fit in LLM input. Only the first {i} datasets are included.]\n"
                break
            name = dataset_names[i] if dataset_names and i < len(dataset_names) else f"Dataset {i+1}"
            block = f"\n---\nDataset: {name}\n"
            # Always try to get scan from explanation if possible
            scan = None
            if isinstance(explanation, dict):
                scan = explanation.get('scan_result')
                if isinstance(scan, str):
                    try:
                        scan = json.loads(scan)
                    except Exception:
                        scan = None
            # Add validator results if available, but only key fields
            mcp = None
            raw_mcp = None
            if validator_results and i < len(validator_results):
                v = validator_results[i]
                if isinstance(v, dict):
                    flags = v.get('flags', [])
                    recs = v.get('recommendations', [])
                    raw_mcp = v.get('validation_result')
                    mcp = raw_mcp
                    if isinstance(mcp, str):
                        try:
                            mcp = json.loads(mcp)
                        except Exception:
                            mcp = None
                    # DEBUG: Print raw and parsed MCP findings to log.txt
                    import datetime
                    log_path = log_file_path or 'log.txt'
                    try:
                        with open(log_path, 'a') as logf:
                            logf.write(f"[MultiDatasetSummariserAgent][DEBUG {datetime.datetime.now()}] RAW MCP findings for dataset {i}: {raw_mcp}\n")
                            logf.write(f"[MultiDatasetSummariserAgent][DEBUG {datetime.datetime.now()}] PARSED MCP findings for dataset {i}: {json.dumps(mcp, indent=2) if mcp else mcp}\n")
                    except Exception:
                        pass
                    # Robust metric extraction: always show real values if present, only 'not calculated' if truly missing
                    def robust_metric(val):
                        if val is None:
                            return 'not calculated'
                        if isinstance(val, str) and val.strip() == '':
                            return 'not calculated'
                        if isinstance(val, (list, dict)) and len(val) == 0:
                            return 'not calculated'
                        if isinstance(val, float) and (val != val):
                            return 'not calculated'
                        return val
                    def infer_threshold(val, fallback):
                        return val if val not in (None, '', 'N/A') else fallback
                    k = mcp.get('k_anonymity', {}) if mcp else {}
                    l = mcp.get('l_diversity', {}) if mcp else {}
                    t = mcp.get('t_closeness', {}) if mcp else {}
                    params = mcp.get('params', {}) if mcp else {}
                    qi_count = len(scan.get('quasi_identifiers', [])) if scan else 'N/A'
                    sensitive_count = len(scan.get('sensitive', [])) if scan else 'N/A'
                    k_req = robust_metric(params.get('k_required')) if params.get('k_required') not in (None, '', 'N/A') else qi_count if qi_count != 0 else 'N/A'
                    l_req = robust_metric(params.get('l_required')) if params.get('l_required') not in (None, '', 'N/A') else sensitive_count if sensitive_count != 0 else 'N/A'
                    t_req = robust_metric(params.get('t_required')) if params.get('t_required') not in (None, '', 'N/A') else 0.2
                    reid_req = robust_metric(params.get('reid_required')) if params.get('reid_required') not in (None, '', 'N/A') else 0.05
                    # Always include MCP findings in detail, matching individual summary style
                    block += "MCP Findings (detailed):\n"
                    block += f"  k-anonymity: min={robust_metric(k.get('k_min'))}, avg={robust_metric(k.get('k_avg'))}, required={k_req}\n"
                    block += f"  l-diversity: min={robust_metric(l.get('l_min'))}, avg={robust_metric(l.get('l_avg'))}, method={robust_metric(l.get('method'))}, required={l_req}\n"
                    block += f"  t-closeness: max={robust_metric(t.get('t_max'))}, avg={robust_metric(t.get('t_avg'))}, method={robust_metric(t.get('method'))}, required={t_req}\n"
                    block += f"  re-identification risk: {reid_req}\n"
            # Extract QI and Sensitive columns from MCP findings if available, else parse from summary text
            qis = []
            sensitive = []
            if mcp and isinstance(mcp, dict):
                params = mcp.get('params', {})
                qis = params.get('qi', [])
                sensitive = params.get('sensitive', [])
            if not qis and scan:
                qis = scan.get('quasi_identifiers', [])
            if not sensitive and scan:
                sensitive = scan.get('sensitive', [])
            # If still empty, try to extract from explanation text using regex and recommended actions
            if not qis or not sensitive:
                import re
                explanation_text = explanation.get('explanation') if isinstance(explanation, dict) else None
                if explanation_text:
                    # Extract QI columns from dedicated section or recommended actions
                    qi_match = re.search(r'\*\*Quasi-Identifiers:\*\*.*?(?:contains|are) (?:the )?quasi-identifier[s]? "([^"]+)"', explanation_text)
                    if qi_match:
                        qis = [qi_match.group(1)]
                    else:
                        # Try to extract list format
                        qi_list_match = re.search(r'\*\*Quasi-Identifiers:\*\*\s*(.*?)\n', explanation_text)
                        if qi_list_match:
                            qis = [qi.strip() for qi in re.split(r',|and', qi_list_match.group(1)) if qi.strip()]
                    # Fallback: look for recommended actions mentioning QIs
                    if not qis:
                        qiactions = re.findall(r'generaliz(?:e|ation|ing|ed|s|ation/suppression) of (?:the )?([\w_\-]+)', explanation_text, re.IGNORECASE)
                        qis += [q.strip() for q in qiactions if q.strip()]
                        qiactions2 = re.findall(r'suppress(?:ion|ing)? (?:the )?([\w_\-]+)', explanation_text, re.IGNORECASE)
                        qis += [q.strip() for q in qiactions2 if q.strip()]
                        # Also look for bullet points mentioning QIs
                        qibullets = re.findall(r'quasi-identifier[s]? ["\']?([\w_\- ]+)["\']?', explanation_text, re.IGNORECASE)
                        qis += [q.strip() for q in qibullets if q.strip()]
                    # Extract Sensitive columns from dedicated section or recommended actions
                    sens_match = re.search(r'\*\*Sensitive Columns:\*\*.*?is "([^"]+)"', explanation_text)
                    if sens_match:
                        sensitive = [sens_match.group(1)]
                    else:
                        # Try to extract additional sensitive columns
                        sens_list_match = re.search(r'\*\*Sensitive Columns:\*\*\s*(.*?)\n', explanation_text)
                        if sens_list_match:
                            # Look for quoted columns
                            sensitive = re.findall(r'"([^"]+)"', sens_list_match.group(1))
                            # If not quoted, split by comma or 'and'
                            if not sensitive:
                                sensitive = [s.strip() for s in re.split(r',|and', sens_list_match.group(1)) if s.strip()]
                    # Fallback: look for recommended actions mentioning sensitive columns
                    if not sensitive:
                        sensactions = re.findall(r'bin(?:ning|ned|s|ning/handling)? (?:the )?([\w_\-]+)', explanation_text, re.IGNORECASE)
                        sensitive += [s.strip() for s in sensactions if s.strip()]
                        sensactions2 = re.findall(r'handling (?:the )?([\w_\-]+)', explanation_text, re.IGNORECASE)
                        sensitive += [s.strip() for s in sensactions2 if s.strip()]
                        # Also look for bullet points mentioning sensitive columns
                        sensbullets = re.findall(r'sensitive (?:column|attribute|variable)[s]? ["\']?([\w_\- ]+)["\']?', explanation_text, re.IGNORECASE)
                        sensitive += [s.strip() for s in sensbullets if s.strip()]
            # Extra debug log for extracted QI and sensitive columns
            log_path = log_file_path or 'log.txt'
            try:
                with open(log_path, 'a') as logf:
                    logf.write(f"[MultiDatasetSummariserAgent][DEBUG] Dataset {name} EXTRACTED QI columns: {qis}\n")
                    logf.write(f"[MultiDatasetSummariserAgent][DEBUG] Dataset {name} EXTRACTED Sensitive columns: {sensitive}\n")
            except Exception:
                pass
            block += f"Quasi-Identifiers (QI columns): {qis if qis else 'None detected'}\n"
            block += f"Sensitive columns: {sensitive if sensitive else 'None detected'}\n"
            block += ("Instructions: You MUST explicitly list the Quasi-Identifiers (QI columns) and Sensitive columns for this dataset exactly as provided above. "
                      "If the list is empty, write 'None detected'. Do NOT omit these fields or reword them. If any are present, list them by name as shown.\n")
            prompt += block
            used_chars += len(block)

        prompt += ("\nIMPORTANT: At the very top of your summary, clearly state the overall risk level for all datasets combined (e.g., Low, Moderate, High) before any other content.\n"
            "Format the summary as a third-party privacy assessment for another party's system. "
            "Be concise, use plain language, and make the findings easy to understand for non-technical stakeholders.\n"
            "Do not include any date, 'To:', 'From:', or formal letter headers in the summary.\n")

        # DEBUG: Print the full prompt sent to the LLM
        debug_prompt_msg = f"[MultiDatasetSummariserAgent] FULL PROMPT TO LLM:\n{prompt}\n"
        log_path = log_file_path or 'log.txt'
        try:
            with open(log_path, 'a') as logf:
                logf.write(debug_prompt_msg)
        except Exception:
            pass
        if log_event:
            log_event(debug_prompt_msg)
        try:
            summary = gemma_client.summarise_privacy_report(prompt)
        except Exception as e:
            summary = f"[ERROR] LLM summary generation failed: {e}"
        if log_event:
            log_event(f"[MultiDatasetSummariserAgent] Output: {summary}")
        return {"summary": summary}

class ValidatorAgent(LlmAgent):
    def __init__(self):
        super().__init__(
            name="validator",
            model="gemma-3n-e4b-it",
            description="Checks anonymisation/privacy compliance using MCP (k-anonymity, l-diversity, t-closeness, etc.)."
        )
    def run(self, dataset, log_event=None, dataset_path=None, qi_cols=None, sensitive_col=None, external_path=None,
            k_required=None, l_required=None, l_method="distinct", t_required=None, reid_required=None,
            numeric_bins=15, dominance_threshold=0.9, rare_threshold=1, binning_method="fd", t_method="tvd", **kwargs):
        """
        Run full MCP anonymisation validation with all configurable parameters.
        Returns a detailed report including MCP findings and recommended actions.
        """
        import pandas as pd
        import json
        from privacy_validator.anonymisation_validator import AnonymisationValidator
        # Load dataset
        if isinstance(dataset, str) and (dataset.endswith('.csv') or '\n' in dataset):
            if '\n' in dataset and not dataset.endswith('.csv'):
                # Assume CSV string
                from io import StringIO
                df = pd.read_csv(StringIO(dataset))
            else:
                df = pd.read_csv(dataset)
        else:
            df = pd.DataFrame(dataset)
        aux_df = None
        if external_path:
            aux_df = pd.read_csv(external_path)
        validator = AnonymisationValidator(df)
        # Use default params if not provided
        if not qi_cols:
            qi_cols = list(df.columns)[:1]  # fallback: first column
        if not sensitive_col:
            sensitive_col = df.columns[-1]  # fallback: last column

        # Get suggested thresholds from the validator
        suggested = validator.suggest_thresholds(qi_cols, sensitive_col)
        k_val = k_required if k_required is not None else suggested.get("k")
        l_val = l_required if l_required is not None else suggested.get("l")
        t_val = t_required if t_required is not None else suggested.get("t")
        reid_val = reid_required if reid_required is not None else suggested.get("reid_probability")

        report = validator.full_report(
            qi_cols=qi_cols,
            sensitive_col=sensitive_col,
            k_required=k_val,
            l_required=l_val,
            l_method=l_method,
            t_required=t_val,
            reid_required=reid_val,
            numeric_bins=numeric_bins,
            external_df=aux_df,
            dominance_threshold=dominance_threshold,
            rare_threshold=rare_threshold,
            binning_method=binning_method,
            t_method=t_method
        )
        # DEBUG: Print MCP findings and all computed metric values before returning
        import datetime
        debug_msg = f"[DEBUG {datetime.datetime.now()}] ValidatorAgent MCP findings: {json.dumps(report, indent=2)}\n"
        if log_event:
            log_event(debug_msg)
        else:
            # Write debug log to log.txt in results directory
            try:
                with open('log.txt', 'a') as logf:
                    logf.write(debug_msg)
            except Exception as e:
                pass
        return {"validation_result": report} 

class ScannerAgent(LlmAgent):
    def __init__(self):
        super().__init__(
            name="scanner",
            model="gemma-3n-e4b-it",
            description="Scans for privacy risks and classifies columns using LLM."
        )
    def run(self, log_event=None, search_glob="**/*.csv", log_file_path=None, **kwargs):
        """
        MCP tool: Discover all tabular datasets (CSV) in the repository and use the LLM to classify QI and sensitive columns.
        """
        import pandas as pd
        dataset_paths = discover_tabular_datasets()
        results = []
        for path in dataset_paths:
            qis = []
            sensitive = []
            try:
                df = pd.read_csv(path, nrows=1)
                columns = list(df.columns)
                # Use shared function for LLM-based classification
                log_line = f"[ScannerAgent] Columns for {path}: {columns}"
                if callable(log_event):
                    log_event(log_line)
                if log_file_path:
                    try:
                        with open(log_file_path, 'a') as f:
                            f.write(log_line + "\n")
                    except Exception:
                        pass
                try:
                    roles = ask_llm_for_column_roles(columns, log_file_path=log_file_path)
                    log_line2 = f"[ScannerAgent] ask_llm_for_column_roles result for {path}: {roles}"
                    if callable(log_event):
                        log_event(log_line2)
                    if log_file_path:
                        try:
                            with open(log_file_path, 'a') as f:
                                f.write(log_line2 + "\n")
                        except Exception:
                            pass
                    qis = roles.get("quasi_identifiers", [])
                    sensitive = roles.get("sensitive", [])
                except Exception as e:
                    log_line3 = f"[ScannerAgent] ask_llm_for_column_roles error for {path}: {e}"
                    if callable(log_event):
                        log_event(log_line3)
                    if log_file_path:
                        try:
                            with open(log_file_path, 'a') as f:
                                f.write(log_line3 + "\n")
                        except Exception:
                            pass
            except Exception as e:
                log_line4 = f"[ScannerAgent] Failed to read {path}: {e}"
                if callable(log_event):
                    log_event(log_line4)
                if log_file_path:
                    try:
                        with open(log_file_path, 'a') as f:
                            f.write(log_line4 + "\n")
                    except Exception:
                        pass
            results.append({
                "path": path,
                "quasi_identifiers": qis,
                "sensitive": sensitive
            })
        log_line5 = f"[ScannerAgent] Discovered datasets with QI/sensitive: {results}"
        if callable(log_event):
            log_event(log_line5)
        if log_file_path:
            try:
                with open(log_file_path, 'a') as f:
                    f.write(log_line5 + "\n")
            except Exception:
                pass
        return {"discovered_datasets": results}

class SummariserAgent(LlmAgent):
    def __init__(self):
        super().__init__(
            name="summariser",
            model="gemma-3n-e4b-it",
            description="Generates third-party privacy summaries for a single dataset using the Gemma LLM as an MCP tool."
        )
    def run(self, validation_result, scan_result, dataset_names=None, log_event=None, dataset_path=None, log_file_path=None, **kwargs):
        """
        Generate a third-party privacy summary for a single dataset using the Gemma LLM as an MCP tool.
        - Summarises privacy risks, recommendations, and Model Context Protocol findings for the dataset.
        - Delegates summary construction to the LLM via gemma_client.summarise_privacy_report.
        - Truncates input to fit within LLM token limits.
        """
       
        # Helper to truncate text to a max number of characters (approx. 4 chars per token)
        def truncate(text, max_chars):
            if len(text) > max_chars:
                return text[:max_chars] + "... [truncated]"
            return text

        # Conservative estimate: 8192 tokens * 4 chars/token = 32,768 chars
        # Reserve 2,000 chars for instructions and formatting
        MAX_PROMPT_CHARS = 30000
        MAX_BLOCK = 6000  # chars for all dataset info

        dataset_str = ", ".join(dataset_names) if dataset_names else "This dataset"

        prompt = (
            "System: Data Privacy Impact Assessment & Reporting\n"
            f"You are a third-party privacy auditor. Given the following dataset and its privacy scan results, generate a clear, actionable, and human-readable summary for a non-technical audience. Include:\n"
            f"- The dataset name (no file paths): {dataset_str}\n"
            "- Any privacy risks or flags, with a brief explanation\n"
            "- Recommended actions (if any)\n"
            "- Model Context Protocol findings: k-anonymity, l-diversity, t-closeness, re-identification risk, and the threshold values used\n"
            "- An explicit risk level for this dataset (e.g., Low, Moderate, High), based on the findings\n"
            "Only metrics relevant or computable for this dataset are shown. If a metric is missing, not met, or not applicable, it is due to the dataset's characteristics or privacy analysis logic—not a system limitation.\n\n"
            "Metric explanations (include these in the summary):\n"
            "- k-anonymity: Measures how well data can be disguised within a group. Low k-anonymity means individuals may be more easily re-identified.\n"
            "- l-diversity: Ensures that within each group, there is a sufficient number of distinct values for sensitive attributes. Low l-diversity means sensitive values are too similar within groups.\n"
            "- t-closeness: Measures how close the distribution of a sensitive attribute in a group is to the distribution in the overall dataset. High t-closeness indicates a higher risk of attribute disclosure.\n"
            "- Re-identification risk: Estimates the probability that an individual can be re-identified from the dataset, given the quasi-identifiers and sensitive attributes. A higher value means a greater risk of re-identification.\n"
            "Definitions for metric status (include these in the summary):\n"
            "- Not met: The metric was evaluated, but the dataset did not satisfy the required threshold (e.g., k-anonymity threshold was set, but the data did not reach it).\n"
            "- Not applicable: The metric does not apply to the dataset, often because of its structure, content, or the privacy configuration (e.g., t-closeness is only relevant for certain types of sensitive data).\n"
            "- Omitted: The metric was not calculated at all, either because the Model Context Protocol tool determined it was unnecessary, the dataset lacked the required attributes, or the scan configuration did not request it.\n\n"
            "At the end, provide a short overall assessment and next steps for ongoing privacy protection.\n\n"
            "Dataset and results:\n"
        )

        block = ""
        # Add validator results (only key fields)
        try:
            v = json.loads(validation_result) if isinstance(validation_result, str) else validation_result
        except Exception:
            v = {}
        try:
            scan = json.loads(scan_result) if isinstance(scan_result, str) else scan_result
        except Exception:
            scan = {}

        # Robustly extract MCP findings from either top-level or nested dict
        import datetime
        import json as _json
        # Prefer nested 'validation_result' if present, else use v itself
        mcp_debug = v.get('validation_result') if isinstance(v, dict) and 'validation_result' in v else v
        if isinstance(mcp_debug, str):
            try:
                mcp_debug = _json.loads(mcp_debug)
            except Exception:
                mcp_debug = None
        debug_msg = f"[DEBUG {datetime.datetime.now()}] MCP findings (pre-summary): { _json.dumps(mcp_debug, indent=2) }\n"
        if log_event:
            log_event(debug_msg)
        else:
            log_path = log_file_path or 'log.txt'
            try:
                with open(log_path, 'a') as logf:
                    logf.write(debug_msg)
            except Exception:
                pass

        # Extract MCP findings robustly
        flags = v.get('flags', []) if isinstance(v, dict) else []
        recs = v.get('recommendations', []) if isinstance(v, dict) else []
        # Use nested 'validation_result' if present, else v itself
        mcp = v.get('validation_result') if isinstance(v, dict) and 'validation_result' in v else v
        if isinstance(mcp, str):
            try:
                mcp = json.loads(mcp)
            except Exception:
                mcp = None
        risk_flags = []
        repair_suggestions = []
        if mcp:
            risk_flags = mcp.get('risk_flags', [])
            repair_suggestions = mcp.get('repair_suggestions', [])

        block += f"Flags: {truncate(str(flags), 300)}\n"
        block += f"Recommendations: {truncate(str(recs), 300)}\n"
        block += f"Risk Flags: {truncate(str(risk_flags), 300)}\n"
        block += f"Repair Suggestions: {truncate(str(repair_suggestions), 300)}\n"

        # Always require thresholds, fallback to QI/sensitive count if missing, and robustly extract real metric values
        def safe_metric(val):
            if val is None or (isinstance(val, float) and (val != val)):
                return 'not calculated'
            return val
        def infer_threshold(val, fallback):
            return val if val not in (None, '', 'N/A') else fallback


        def robust_metric(val):
            # Return 'not calculated' for None, empty string, empty list, or NaN, else the value
            if val is None:
                return 'not calculated'
            if isinstance(val, str) and val.strip() == '':
                return 'not calculated'
            if isinstance(val, (list, dict)) and len(val) == 0:
                return 'not calculated'
            if isinstance(val, float) and (val != val):
                return 'not calculated'
            return val

        k = mcp.get('k_anonymity', {}) if mcp else {}
        l = mcp.get('l_diversity', {}) if mcp else {}
        t = mcp.get('t_closeness', {}) if mcp else {}
        params = mcp.get('params', {}) if mcp else {}
        qi_count = len(scan.get('quasi_identifiers', [])) if scan else 'N/A'
        sensitive_count = len(scan.get('sensitive', [])) if scan else 'N/A'
        k_req = robust_metric(params.get('k_required')) if params.get('k_required') not in (None, '', 'N/A') else qi_count if qi_count != 0 else 'N/A'
        l_req = robust_metric(params.get('l_required')) if params.get('l_required') not in (None, '', 'N/A') else sensitive_count if sensitive_count != 0 else 'N/A'
        t_req = robust_metric(params.get('t_required')) if params.get('t_required') not in (None, '', 'N/A') else 0.2
        reid_req = robust_metric(params.get('reid_required')) if params.get('reid_required') not in (None, '', 'N/A') else 0.05

        block += "Model Context Protocol Findings:\n"
        block += f"- k-anonymity: {robust_metric(k.get('k_min')) if k.get('k_min') is not None else 'Not calculated'}. "
        block += f"The minimum group size was {robust_metric(k.get('k_min'))}, average was {robust_metric(k.get('k_avg'))}, required threshold: {k_req}.\n"
        block += f"- l-diversity: {robust_metric(l.get('l_min')) if l.get('l_min') is not None else 'Not calculated'}. "
        block += f"The minimum diversity was {robust_metric(l.get('l_min'))}, average was {robust_metric(l.get('l_avg'))}, method: {robust_metric(l.get('method'))}, required threshold: {l_req}.\n"
        block += f"- t-closeness: {robust_metric(t.get('t_max')) if t.get('t_max') is not None else 'Not calculated'}. "
        block += f"The maximum closeness was {robust_metric(t.get('t_max'))}, average was {robust_metric(t.get('t_avg'))}, method: {robust_metric(t.get('method'))}, required threshold: {t_req}.\n"
        block += f"- Re-identification risk: {reid_req if reid_req is not None else 'Not calculated'}. "
        block += f"The dataset was evaluated against a risk threshold of {reid_req}.\n"
        # Always extract QI and sensitive columns from MCP findings params['qi'] and params['sensitive'] if present
        qis = []
        sensitive = []
        if params:
            qis = params.get('qi', [])
            sensitive = params.get('sensitive', [])
        if not qis and scan:
            qis = scan.get('quasi_identifiers', [])
        if not sensitive and scan:
            sensitive = scan.get('sensitive', [])
        debug_cols_msg = f"[DEBUG] QI columns passed to summary: {qis}\n[DEBUG] Sensitive columns passed to summary: {sensitive}\n"
        if log_event:
            log_event(debug_cols_msg)
        else:
            log_path = log_file_path or 'log.txt'
            try:
                with open(log_path, 'a') as logf:
                    logf.write(debug_cols_msg)
            except Exception:
                pass
        block += f"Quasi-Identifiers: {truncate(str(qis), 200)}\n"
        block += f"Sensitive Columns: {truncate(str(sensitive), 200)}\n"
        block = truncate(block, MAX_BLOCK)

        prompt += block
        prompt += ("\nFormat the summary as a third-party privacy assessment for another party's system. "
                   "Be concise, use plain language, and make the findings easy to understand for non-technical stakeholders.\n"
                   "Do not include any date, 'To:', 'From:', or formal letter headers in the summary.\n")

        if log_event:
            log_event(f"[SummariserAgent] Prompt to LLM: {prompt}")
        # Always write prompt to log.txt for persistent debug
        log_path = log_file_path or 'log.txt'
        try:
            with open(log_path, 'a') as logf:
                logf.write(f"[SummariserAgent] Prompt to LLM: {prompt}\n")
        except Exception:
            pass
        try:
            summary = gemma_client.summarise_privacy_report(prompt)
        except Exception as e:
            summary = f"[ERROR] LLM summary generation failed: {e}"
        if log_event:
            log_event(f"[SummariserAgent] Output for {dataset_path}: {summary}")
        return {"summary": summary}

class OrchestratorAgent:
    def __init__(self):
        """
        OrchestratorAgent coordinates the workflow between ValidatorAgent, ScannerAgent, and SummariserAgent.
        Discovers agent endpoints and aggregates results.
        """
        import requests
        self.agent_services = {
            "validator": "http://localhost:8001",
            "scanner": "http://localhost:8002",
            "summariser": "http://localhost:8003"
        }
        self.agent_cards = {}
        # Discover agent cards
        errors = []
        for name, url in self.agent_services.items():
            try:
                card = requests.get(f"{url}/.well-known/agent.json").json()
                self.agent_cards[name] = card
            except Exception as e:
                errors.append(f"{name}: {e}")
        if len(self.agent_cards) < len(self.agent_services):
            raise RuntimeError(f"Agent card discovery failed for: {', '.join(errors)}. Ensure all agent services are running.")

    def run(self, dataset, log_event=None, dataset_path=None, log_dir=None):
        """
        Run the full privacy validation, scanning, and summarisation workflow for a dataset.
        Returns validation, scan, and summary results. Logs workflow events.
        """
        import requests
        import json
        import os
        from datetime import datetime
        import glob
        # If log_dir is not provided, use the most recent results/<timestamp> directory
        if log_dir is None:
            results_root = os.path.join(os.path.dirname(__file__), '../results')
            results_root = os.path.abspath(results_root)
            subdirs = [d for d in glob.glob(os.path.join(results_root, '*/')) if os.path.isdir(d)]
            if subdirs:
                # Sort by timestamp descending
                subdirs.sort(reverse=True)
                log_dir = subdirs[0].rstrip('/')
            else:
                # Fallback: create a new timestamped directory
                log_dir = os.path.join(results_root, datetime.now().strftime('results/%Y-%m-%dT%H-%M-%S-%fZ'))
        logs = []
        def log_event_local(event):
            logs.append(f"{datetime.now().isoformat()} {event}")
            if log_event:
                log_event(event)

        def safe_post(url, payload, agent_name):
            try:
                resp = requests.post(url, json=payload)
                log_event_local(f"POST {agent_name} {url} payload={payload} status={resp.status_code}")
                if resp.status_code != 200:
                    log_event_local(f"{agent_name} error: {resp.text}")
                    return {"error": f"{agent_name} returned status {resp.status_code}", "response": resp.text}
                try:
                    result = resp.json()
                    log_event_local(f"{agent_name} response: {result}")
                    return result
                except json.JSONDecodeError:
                    log_event_local(f"{agent_name} invalid JSON: {resp.text}")
                    return {"error": f"{agent_name} returned invalid JSON", "response": resp.text}
            except Exception as e:
                log_event_local(f"{agent_name} request failed: {str(e)}")
                return {"error": f"{agent_name} request failed: {str(e)}"}

        log_event_local(f"[OrchestratorAgent] Starting workflow for {dataset_path}")
        # A2A: POST to scanner FIRST
        scanner_url = self.agent_services["scanner"] + self.agent_cards["scanner"]["endpoint"]
        # Pass log_file_path to agents
        log_file_path = os.path.join(log_dir, "log.txt") if log_dir else "log.txt"
        scan = safe_post(scanner_url, {"dataset": dataset, "dataset_path": dataset_path, "log_file_path": log_file_path}, "scanner")

        # Extract QI and sensitive columns for this dataset
        qi_cols = None
        sensitive_col = None
        if scan and "discovered_datasets" in scan:
            # Find the entry for this dataset
            for entry in scan["discovered_datasets"]:
                if (entry.get("path") == dataset_path) or (os.path.basename(entry.get("path","")) == os.path.basename(dataset_path)):
                    qis = entry.get("quasi_identifiers", [])
                    sens = entry.get("sensitive", [])
                    qi_cols = qis if qis else None
                    sensitive_col = sens[0] if sens else None
                    break

        # A2A: POST to validator, passing QI and sensitive if found
        validator_url = self.agent_services["validator"] + self.agent_cards["validator"]["endpoint"]
        validator_payload = {"dataset": dataset, "dataset_path": dataset_path}
        if qi_cols:
            validator_payload["qi_cols"] = qi_cols
        if sensitive_col:
            validator_payload["sensitive_col"] = sensitive_col
        validation = safe_post(validator_url, validator_payload, "validator")
        # Debug: log raw validator response
        log_event_local(f"[DEBUG] Raw validator response: {json.dumps(validation, default=str)}")
        # Ensure validation_result is a dict, never None or string
        val_result = validation.get("validation_result", validation)
        if isinstance(val_result, str):
            try:
                val_result = json.loads(val_result)
            except Exception as e:
                log_event_local(f"[ERROR] Could not parse validation_result string: {e}")
                val_result = {}
        if not isinstance(val_result, dict) or val_result is None:
            log_event_local(f"[WARN] validation_result is not a dict or is None. Value: {val_result}")
        # A2A: POST to summariser
        summariser_url = self.agent_services["summariser"] + self.agent_cards["summariser"]["endpoint"]
        summary = safe_post(summariser_url, {
            "datasets": [dataset_path],
            "results": {
                "validation_result": json.dumps(val_result, ensure_ascii=False),
                "scan_result": json.dumps(scan.get("scan_result", scan), ensure_ascii=False)
            },
            "log_file_path": log_file_path
        }, "summariser")
        log_event_local(f"[OrchestratorAgent] Finished workflow for {dataset_path}")
        # Write logs to log.txt in the scan's timestamp folder
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "log.txt"), "a") as f:
                for line in logs:
                    f.write(line + "\n")
        return {
            "validation": validation,
            "scan": scan,
            "summary": summary
        }
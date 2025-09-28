
"""
MCP (Model Context Protocol) anonymisation validator for privacy monitoring.
Implements k-anonymity, l-diversity, t-closeness, and linkage attack simulation.
Provides full privacy risk report and threshold suggestions for datasets.
"""

import os
import tempfile
import math
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, wasserstein_distance  # For categorical association and EMD

# -----------------------------
# Utility Functions
# -----------------------------
def _safe_entropy(p: np.ndarray) -> float:
    """
    Compute Shannon entropy (base-2) for distribution p (ignoring zero probabilities).
    """
    p = p[p > 0]
    if p.size == 0:
        return 0.0
    return float(-(p * np.log2(p)).sum())

def _total_variation_distance(p: np.ndarray, q: np.ndarray) -> float:
    """
    Compute Total Variation Distance (TVD) between two distributions.
    """
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    p = p / p.sum() if p.sum() > 0 else p
    q = q / q.sum() if q.sum() > 0 else q
    return 0.5 * np.abs(p - q).sum()

def _emd_distance(p_values: np.ndarray, q_values: np.ndarray) -> float:
    """
    Compute Earth Mover's Distance (EMD) / Wasserstein distance for numeric distributions.
    """
    return float(wasserstein_distance(p_values, q_values))

def simulate_linkage_attack(anonymised_df: pd.DataFrame, aux_df: pd.DataFrame, qi_cols: List[str]) -> Dict[str, Any]:
    """
    Simulate a robust linkage attack (row-level):
    - Unique: aux record maps to exactly 1 row in anonymised_df
    - Multiple: aux record maps to more than 1 row
    - None: aux record maps to 0 rows
    Returns counts, flagged aux rows that had unique match, and re-identification probability.
    """
    aux = aux_df.copy().reset_index(drop=False).rename(columns={"index": "__aux_id__"})
    merged = aux.merge(anonymised_df, on=qi_cols, how="left", indicator=True)
    counts = merged.groupby("__aux_id__")["_merge"].apply(lambda s: (s == "both").sum())

    unique = int((counts == 1).sum())
    multiple = int((counts > 1).sum())
    none = int((counts == 0).sum())
    flagged = aux.loc[counts[counts == 1].index].drop(columns="__aux_id__", errors="ignore").to_dict("records")
    reid_prob = float(unique / len(aux)) if len(aux) else 0.0

    return {
        "unique": unique,
        "multiple": multiple,
        "none": none,
        "flagged": flagged,
        "records_tested": len(aux),
        "reid_probability": reid_prob,
    }

# -----------------------------
# Data classes for reports
# -----------------------------
@dataclass
class KAnonymityReport:
    k_min: int
    k_avg: float
    eq_class_size_hist: Dict[int, int]

@dataclass
class LDiversityReport:
    method: str
    l_min: float
    l_avg: float
    entropy_min: Optional[float] = None
    entropy_avg: Optional[float] = None
    entropy_effective_min: Optional[float] = None
    entropy_effective_avg: Optional[float] = None

@dataclass
class TClosenessReport:
    t_max: float
    t_avg: float
    bins: Optional[List[float]] = None
    method: str = "tvd"

# -----------------------------
# Core Validator
# -----------------------------
class AnonymisationValidator:

    def l_diversity(self, qi_cols: List[str], sensitive_col: str, method: str = "distinct") -> LDiversityReport:
        """
        Compute l-diversity for the given quasi-identifier columns and sensitive attribute.
        method: 'distinct' (default) or 'entropy'.
        Returns an LDiversityReport dataclass.
        """
        grp = self.df.groupby(qi_cols, dropna=False)[sensitive_col]
        if method == "distinct":
            l_values = grp.nunique(dropna=False)
            l_min = float(l_values.min()) if len(l_values) else 0.0
            l_avg = float(l_values.mean()) if len(l_values) else 0.0
            return LDiversityReport(method=method, l_min=l_min, l_avg=l_avg)
        elif method == "entropy":
            probs = grp.value_counts(normalize=True, dropna=False)
            entropies = probs.groupby(level=list(range(len(qi_cols)))).apply(lambda p: _safe_entropy(p.values))
            entropy_min = float(entropies.min()) if len(entropies) else 0.0
            entropy_avg = float(entropies.mean()) if len(entropies) else 0.0
            entropy_eff_min = float(2 ** entropy_min)
            entropy_eff_avg = float(2 ** entropy_avg)
            distinct_l = grp.nunique(dropna=False)
            distinct_min = float(distinct_l.min()) if len(distinct_l) else 0.0
            distinct_avg = float(distinct_l.mean()) if len(distinct_l) else 0.0
            return LDiversityReport(
                method=method,
                l_min=distinct_min,
                l_avg=distinct_avg,
                entropy_min=entropy_min,
                entropy_avg=entropy_avg,
                entropy_effective_min=entropy_eff_min,
                entropy_effective_avg=entropy_eff_avg,
            )
        else:
            raise ValueError("method must be 'distinct' or 'entropy'")

    def k_anonymity(self, qi_cols: List[str]) -> KAnonymityReport:
        """
        Compute k-anonymity statistics for the given quasi-identifier columns.
        Returns a KAnonymityReport dataclass with min, avg, and equivalence class size histogram.
        """
        grouped = self.df.groupby(qi_cols, dropna=False)
        eq_class_sizes = grouped.size()
        k_min = int(eq_class_sizes.min()) if len(eq_class_sizes) else 0
        k_avg = float(eq_class_sizes.mean()) if len(eq_class_sizes) else 0.0
        hist = eq_class_sizes.value_counts().sort_index().to_dict()
        return KAnonymityReport(k_min=k_min, k_avg=k_avg, eq_class_size_hist=hist)
    def __init__(self, df: pd.DataFrame):
        """
        Initialize the AnonymisationValidator with a pandas DataFrame.
        Args:
            df (pd.DataFrame): The dataset to validate for anonymisation.
        """
        self.df = df
    def suggest_thresholds(self, qi_cols, sensitive_col):
        """
        Suggest k, l, t, and re-identification thresholds based on dataset size and column types.
        Returns a dictionary with suggested values for k, l, t, and re-identification probability.
        """
        n_rows = len(self.df)
        # Suggest k-anonymity: at least 5 for small datasets, 10 for medium, 20 for large
        if n_rows < 1000:
            k_suggested = 5
        elif n_rows < 10000:
            k_suggested = 10
        else:
            k_suggested = 20

        # Suggest l-diversity: 2 for categorical, 3 for sensitive with many unique values
        s = self.df[sensitive_col]
        if s.nunique() <= 10:
            l_suggested = 2
        else:
            l_suggested = 3

        # Suggest t-closeness: stricter for more sensitive data
        if s.dtype.kind in {'i', 'f'}:
            t_suggested = 0.2  # Stricter for numeric sensitive attributes
        else:
            t_suggested = 0.3  # Slightly looser for categorical

        # Suggest re-identification probability threshold
        reid_suggested = 0.05 if n_rows > 1000 else 0.1

        return {
            "k": k_suggested,
            "l": l_suggested,
            "t": t_suggested,
            "reid_probability": reid_suggested
        }

    # --- t-closeness ---
    def t_closeness(
        self,
        qi_cols: List[str],
        sensitive_col: str,
        numeric_bins: int = 10,
        binning_method: str = "fd",
        t_method: str = "tvd",
    ) -> TClosenessReport:
        """
        Compute t-closeness for numeric or categorical sensitive attributes.
        t_method: 'tvd' (default) or 'emd' (Earth Mover's Distance)
        Returns a TClosenessReport dataclass.
        """
        s = self.df[sensitive_col]
        bins = None

        if pd.api.types.is_numeric_dtype(s):
            x = s.dropna()
            if x.empty:
                global_dist = np.array([])
                def dist_func(subs: pd.Series) -> float:
                    return 0.0
            else:
                    if binning_method == "quantile":
                        quantiles = np.linspace(0, 1, numeric_bins + 1)
                        bins = np.unique(np.quantile(x, quantiles))
                    else:
                        x_max = x.max()
                        x_min = x.min()
                        if np.isnan(x_max) or np.isnan(x_min):
                            # All values are NaN, skip calculation
                            bins = None
                            global_counts = np.array([])
                            global_probs = np.array([])
                            def dist_func(subs: pd.Series) -> float:
                                return 0.0
                        else:
                            iqr = np.subtract(*np.percentile(x, [75, 25]))
                            h = 2 * iqr * (len(x) ** (-1/3)) if iqr > 0 else (x_max - x_min) / max(1, numeric_bins)
                            # Prevent division by zero or NaN
                            if h == 0 or np.isnan(h):
                                h = 1
                            bin_count = max(1, int(np.ceil((x_max - x_min) / h)))
                            bins = np.histogram_bin_edges(x, bins=bin_count)
                            global_counts, _ = np.histogram(x, bins=bins)
                            global_probs = global_counts / global_counts.sum() if global_counts.sum() > 0 else global_counts
                            def dist_func(subs: pd.Series) -> float:
                                if t_method == "emd":
                                    return _emd_distance(subs.dropna().values, x.values)
                                counts, _ = np.histogram(subs.dropna(), bins=bins)
                                p = counts / counts.sum() if counts.sum() > 0 else counts
                                return _total_variation_distance(p, global_probs)
        else:
            cats = s.dropna().unique()
            global_probs = s.value_counts(normalize=True).reindex(cats, fill_value=0).values
            def dist_func(subs: pd.Series) -> float:
                p = subs.value_counts(normalize=True).reindex(cats, fill_value=0).values
                return _total_variation_distance(p, global_probs)

        t_values = self.df.groupby(qi_cols, dropna=False)[sensitive_col].apply(dist_func)
        t_max = float(t_values.max()) if len(t_values) else 0.0
        t_avg = float(t_values.mean()) if len(t_values) else 0.0
        return TClosenessReport(t_max=t_max, t_avg=t_avg, bins=(bins.tolist() if bins is not None else None), method=t_method)

    # --- Full report ---
    def full_report(
        self,
        qi_cols: List[str],
        sensitive_col: str,
        k_required: Optional[int] = None,
        l_required: Optional[float] = None,
        l_method: str = "distinct",
        t_required: Optional[float] = None,
        reid_required: Optional[float] = None,
        numeric_bins: int = 15,
        external_df: Optional[pd.DataFrame] = None,
        dominance_threshold: float = 0.9,
        rare_threshold: int = 1,
        binning_method: str = "fd",
        t_method: str = "tvd",
    ) -> Dict[str, Any]:
        """
        Generate a full anonymisation report including:
        - MCP findings (k-anonymity, l-diversity, t-closeness)
        - Suggested thresholds
        - Risk flags and repair suggestions
        - Behaviour patterns (rare QI combinations, sensitive skew, QI-sensitive correlation)
        - (Optional) linkage attack simulation
        """
        report: Dict[str, Any] = {}

        # Add suggested thresholds
        suggested = self.suggest_thresholds(qi_cols, sensitive_col)

        report["schema_version"] = "1.0.0"
        report["params"] = {
            "qi": qi_cols,
            "sensitive": sensitive_col,
            "k_required": k_required,
            "l_required": l_required,
            "l_method": l_method,
            "t_required": t_required,
            "numeric_bins": numeric_bins,
            "reid_required": reid_required,
            "dominance_threshold": dominance_threshold,
            "rare_threshold": rare_threshold,
            "binning_method": binning_method,
            "t_method": t_method,
        }
        report["suggested_thresholds"] = suggested

        report["data_summary"] = {
            "n_rows": int(len(self.df)),
            "n_cols": int(self.df.shape[1]),
            "missing_rates": {col: float(self.df[col].isna().mean()) for col in self.df.columns},
        }

        import datetime
        debug_lines = []
        debug_lines.append(f"[DEBUG {datetime.datetime.now()}] Validator input QI columns: {qi_cols}")
        debug_lines.append(f"[DEBUG {datetime.datetime.now()}] Validator input sensitive column: {sensitive_col}")
        # k-anonymity
        try:
            krep = self.k_anonymity(qi_cols)
            k_dict = krep.__dict__
            debug_lines.append(f"[DEBUG {datetime.datetime.now()}] k-anonymity result: {k_dict}")
        except Exception as e:
            k_dict = {"k_min": None, "k_avg": None}
            debug_lines.append(f"[DEBUG {datetime.datetime.now()}] k-anonymity error: {e}")
        # l-diversity
        try:
            lrep = self.l_diversity(qi_cols, sensitive_col, method=l_method)
            ldict = {
                "method": lrep.method,
                "l_min": lrep.l_min,
                "l_avg": lrep.l_avg,
            }
            if lrep.method == "entropy":
                ldict.update({
                    "entropy_min": lrep.entropy_min,
                    "entropy_avg": lrep.entropy_avg,
                    "entropy_effective_min": lrep.entropy_effective_min,
                    "entropy_effective_avg": lrep.entropy_effective_avg,
                })
            debug_lines.append(f"[DEBUG {datetime.datetime.now()}] l-diversity result: {ldict}")
        except Exception as e:
            ldict = {"method": None, "l_min": None, "l_avg": None}
            debug_lines.append(f"[DEBUG {datetime.datetime.now()}] l-diversity error: {e}")
        # t-closeness
        try:
            trep = self.t_closeness(qi_cols, sensitive_col, numeric_bins=numeric_bins, binning_method=binning_method, t_method=t_method)
            t_dict = trep.__dict__
            debug_lines.append(f"[DEBUG {datetime.datetime.now()}] t-closeness result: {t_dict}")
        except Exception as e:
            t_dict = {"t_max": None, "t_avg": None, "method": None}
            debug_lines.append(f"[DEBUG {datetime.datetime.now()}] t-closeness error: {e}")
        # Write debug lines to log.txt
        try:
            with open('log.txt', 'a') as logf:
                for line in debug_lines:
                    logf.write(line + "\n")
        except Exception:
            pass
        report["k_anonymity"] = k_dict
        report["l_diversity"] = ldict
        report["t_closeness"] = t_dict
        report["k_anonymity"] = k_dict
        report["l_diversity"] = ldict
        report["t_closeness"] = t_dict

        # -----------------------------
        # Risk flags and repair suggestions
        # -----------------------------
        flags = []
        repairs = []

        if k_required is not None and krep.k_min < k_required:
            flags.append(f"k-anonymity below threshold: {krep.k_min} < {k_required}")
            repairs.append(f"Consider generalising or suppressing QIs: {qi_cols}")

        if l_required is not None:
            if l_method == "entropy":
                if lrep.entropy_effective_min < l_required:
                    flags.append(f"entropy l-diversity (effective) below threshold: {lrep.entropy_effective_min:.3f} < {l_required}")
                    repairs.append(f"Consider generalising QIs or grouping sensitive values to increase entropy.")
            else:
                if lrep.l_min < l_required:
                    flags.append(f"l-diversity (distinct) below threshold: {lrep.l_min} < {l_required}")
                    repairs.append(f"Consider generalising QIs to increase diversity.")

        if t_required is not None and trep.t_max > t_required:
            flags.append(f"t-closeness above threshold: {trep.t_max:.4f} > {t_required}")
            repairs.append(f"Consider generalising QIs or binning sensitive variable differently.")

        if external_df is not None:
            attack_results = simulate_linkage_attack(self.df, external_df, qi_cols)
            report["attack_simulation"] = attack_results
            if reid_required is not None and attack_results["reid_probability"] > reid_required:
                flags.append(f"Re-identification probability too high: {attack_results['reid_probability']:.2f} > {reid_required}")
                repairs.append("Consider suppressing unique QI combinations or generalising QIs.")

        report["risk_flags"] = flags
        report["repair_suggestions"] = repairs

        # -----------------------------
        # Behaviour patterns
        # -----------------------------
        behaviour_patterns = {
            "rare_combinations": [],
            "sensitive_skew": [],
            "qi_sensitive_correlation": []
        }

        grouped = self.df.groupby(qi_cols, dropna=False)
        for qi_vals, group in grouped:
            if len(group) <= rare_threshold:
                behaviour_patterns["rare_combinations"].append({
                    "qi_values": dict(zip(qi_cols, qi_vals if isinstance(qi_vals, tuple) else [qi_vals])),
                    "count": int(len(group))
                })
            dist = group[sensitive_col].value_counts(normalize=True, dropna=False)
            if not dist.empty and dist.max() > dominance_threshold:
                behaviour_patterns["sensitive_skew"].append({
                    "qi_values": dict(zip(qi_cols, qi_vals if isinstance(qi_vals, tuple) else [qi_vals])),
                    "dominant_sensitive": str(dist.idxmax()),
                    "frequency": float(dist.max())
                })

        try:
            s = self.df[sensitive_col]
            if pd.api.types.is_numeric_dtype(s):
                for qi in qi_cols:
                    if pd.api.types.is_numeric_dtype(self.df[qi]):
                        corr = float(self.df[[qi, sensitive_col]].corr().iloc[0, 1])
                        if abs(corr) > 0.5:
                            behaviour_patterns["qi_sensitive_correlation"].append({
                                "qi": qi,
                                "sensitive": sensitive_col,
                                "correlation": corr
                            })
            else:
                n = len(self.df)
                for qi in qi_cols:
                    table = pd.crosstab(self.df[qi], s)
                    if table.size == 0 or n == 0:
                        continue
                    chi2, p, dof, expected = chi2_contingency(table, correction=False)
                    r, c = table.shape
                    denom = n * (min(r - 1, c - 1) if min(r - 1, c - 1) > 0 else 1)
                    cramers_v = math.sqrt(chi2 / denom) if denom > 0 else 0.0
                    if cramers_v > 0.2:
                        behaviour_patterns["qi_sensitive_correlation"].append({
                            "qi": qi,
                            "sensitive": sensitive_col,
                            "association_cramers_v": float(cramers_v),
                            "chi2": float(chi2),
                            "p_value": float(p)
                        })
        except Exception as e:
            behaviour_patterns["correlation_error"] = str(e)

        report["behaviour_patterns"] = behaviour_patterns
        return report
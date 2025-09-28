import argparse
import pandas as pd
import json
import os
import tempfile
import numpy as np
from privacy_validator.anonymisation_validator import AnonymisationValidator

def _json_converter(o):
    if isinstance(o, (np.integer, )):
        return int(o)
    if isinstance(o, (np.floating, )):
        return float(o)
    if isinstance(o, (np.ndarray, )):
        return o.tolist()
    return str(o)

def atomic_write_json(path: str, obj):
    dirn = os.path.dirname(path) or "."
    os.makedirs(dirn, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="tmp_report_", dir=dirn, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf8") as f:
            json.dump(obj, f, indent=2, default=_json_converter)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to anonymised CSV")
    parser.add_argument("--external", help="Path to auxiliary dataset CSV (optional)")
    parser.add_argument("--qi", nargs="+", required=True, help="Quasi-identifier columns")
    parser.add_argument("--sensitive", required=True, help="Sensitive attribute column")
    parser.add_argument("--k", type=int, default=5, help="Required k-anonymity")
    parser.add_argument("--l", type=float, default=2, help="Required l-diversity")
    parser.add_argument("--l-method", choices=["entropy", "distinct"], default="entropy", help="l-diversity method")
    parser.add_argument("--reid-probability", type=float, default=0.05, help="Allowed re-identification probability")
    parser.add_argument("--t", type=float, default=0.2, help="Required t-closeness")
    parser.add_argument("--numeric-bins", type=int, default=15, help="Bins for numeric t-closeness")
    parser.add_argument("--out", required=True, help="Output JSON report path")
    parser.add_argument("--dominance-threshold", type=float, default=0.9, help="Frequency threshold for sensitive dominance in a group")
    parser.add_argument("--rare-threshold", type=int, default=1, help="Max group size to consider 'rare' (e.g., <= 1)")
    parser.add_argument("--binning-method", choices=["fd", "quantile"], default="fd", help="Binning method for numeric sensitive attribute")
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    aux_df = pd.read_csv(args.external) if args.external else None

    # basic validations
    missing_cols = [c for c in args.qi + [args.sensitive] if c not in df.columns]
    if missing_cols:
        raise SystemExit(f"ERROR: Missing columns in data: {missing_cols}")

    if aux_df is not None:
        missing_aux = [c for c in args.qi if c not in aux_df.columns]
        if missing_aux:
            raise SystemExit(f"ERROR: Missing QI columns in external aux data: {missing_aux}")

    validator = AnonymisationValidator(df)
    report = validator.full_report(
        qi_cols=args.qi,
        sensitive_col=args.sensitive,
        k_required=args.k,
        l_required=args.l,
        l_method=args.l_method,
        t_required=args.t,
        reid_required=args.reid_probability,
        numeric_bins=args.numeric_bins,
        external_df=aux_df,
        dominance_threshold=args.dominance_threshold,
        rare_threshold=args.rare_threshold,
        binning_method=args.binning_method,
    )
    atomic_write_json(args.out, report)
    print(f"Anonymisation report saved to {args.out}")

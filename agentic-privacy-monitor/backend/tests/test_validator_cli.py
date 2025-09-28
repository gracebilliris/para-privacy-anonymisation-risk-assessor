import pandas as pd
from privacy_validator.anonymisation_validator import AnonymisationValidator

def run_test(df, qi, sensitive, k_required, l_required, t_required, desc):
    """
    Run a single anonymisation validation test and print results.
    """
    validator = AnonymisationValidator(df)
    report = validator.full_report(
        qi_cols=qi,
        sensitive_col=sensitive,
        k_required=k_required,
        l_required=l_required,
        t_required=t_required
    )

    print(f"\nTest: {desc}")
    print("Report:", report)
    if report.get("risk_flags"):
        print("❌ Risk flags:", report["risk_flags"])
    else:
        print("✅ All thresholds met.")

# ------------------------------
# GOOD CASE: Meets all thresholds
# ------------------------------
df_good = pd.DataFrame({
    "age_band": ["20-29", "20-29", "30-39", "30-39"],
    "postcode_prefix": ["AB1", "AB1", "AB2", "AB2"],
    "gender": ["Male", "Female", "Male", "Female"],
    "diagnosis": ["Flu", "Flu", "Cold", "Cold"]
})
run_test(df_good, ["age_band", "postcode_prefix", "gender"], "diagnosis", k_required=2, l_required=1, t_required=0.5, desc="Good anonymised data")

# ---------------------------------
# BAD CASE: Fails k-anonymity
# ---------------------------------
df_bad_k = pd.DataFrame({
    "age_band": ["20-29", "30-39"],
    "postcode_prefix": ["AB1", "AB2"],
    "gender": ["Male", "Female"],
    "diagnosis": ["Flu", "Cold"]
})
run_test(df_bad_k, ["age_band", "postcode_prefix", "gender"], "diagnosis", k_required=2, l_required=1, t_required=0.5, desc="Bad k-anonymity")

# ---------------------------------
# BAD CASE: Fails l-diversity
# ---------------------------------
df_bad_l = pd.DataFrame({
    "age_band": ["20-29", "20-29", "30-39", "30-39"],
    "postcode_prefix": ["AB1", "AB1", "AB2", "AB2"],
    "gender": ["Male", "Male", "Female", "Female"],
    "diagnosis": ["Flu", "Flu", "Flu", "Flu"]
})
run_test(df_bad_l, ["age_band", "postcode_prefix", "gender"], "diagnosis", k_required=2, l_required=2, t_required=0.5, desc="Bad l-diversity")

# ---------------------------------
# BAD CASE: Fails t-closeness
# ---------------------------------
df_bad_t = pd.DataFrame({
    "age_band": ["20-29"] * 10 + ["30-39"] * 10,
    "postcode_prefix": ["AB1"] * 10 + ["AB2"] * 10,
    "gender": ["Male"] * 10 + ["Female"] * 10,
    "diagnosis": ["Flu"] * 18 + ["Cold"] * 2
})
run_test(df_bad_t, ["age_band", "postcode_prefix", "gender"], "diagnosis", k_required=2, l_required=1, t_required=0.1, desc="Bad t-closeness")

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from privacy_validator.anonymisation_validator import AnonymisationValidator, simulate_linkage_attack

import pandas as pd
import numpy as np
import pytest

# -----------------------------
# Fixtures
# -----------------------------
@pytest.fixture
def simple_df():
    """Tiny dataset with clear groups for testing.

    Columns:
    - age_band: categorical quasi-identifier
    - zip: categorical quasi-identifier
    - disease: sensitive attribute
    - income: numeric sensitive attribute
    """
    return pd.DataFrame({
        "age_band": ["20-29", "20-29", "30-39", "30-39", "30-39"],
        "zip": ["12345", "12345", "54321", "54321", "54321"],
        "disease": ["HIV", "Flu", "HIV", "HIV", "Cancer"],
        "income": [50, 60, 70, 80, 90],
    })

# -----------------------------
# K-anonymity tests
# -----------------------------
def test_k_anonymity_min_and_avg(simple_df):
    """Check minimum and average k-anonymity on grouped quasi-identifiers."""
    v = AnonymisationValidator(simple_df)
    report = v.k_anonymity(["age_band", "zip"])
    # Two equivalence classes: size=2 and size=3
    assert report.k_min == 2
    assert pytest.approx(report.k_avg, 0.01) == 2.5
    assert report.eq_class_size_hist == {2: 1, 3: 1}

# -----------------------------
# L-diversity tests
# -----------------------------
def test_l_diversity_distinct(simple_df):
    """Test distinct l-diversity calculation."""
    v = AnonymisationValidator(simple_df)
    report = v.l_diversity(["age_band", "zip"], "disease", method="distinct")
    assert report.l_min == 2
    assert report.l_avg == 2.0

def test_l_diversity_entropy(simple_df):
    """Test entropy l-diversity calculation with effective-l."""
    v = AnonymisationValidator(simple_df)
    report = v.l_diversity(["age_band", "zip"], "disease", method="entropy")
    assert report.l_min >= 0
    assert report.l_avg > 0
    # Effective-l should be positive
    assert report.entropy_effective_min >= 1.0
    assert report.entropy_effective_avg >= 1.0

# -----------------------------
# T-closeness tests
# -----------------------------
def test_t_closeness_categorical(simple_df):
    """Check t-closeness on categorical sensitive attribute."""
    v = AnonymisationValidator(simple_df)
    report = v.t_closeness(["age_band", "zip"], "disease", numeric_bins=5)
    assert 0 <= report.t_max <= 1
    assert 0 <= report.t_avg <= 1

def test_t_closeness_numeric(simple_df):
    """Check t-closeness on numeric sensitive attribute."""
    v = AnonymisationValidator(simple_df)
    report = v.t_closeness(["age_band", "zip"], "income", numeric_bins=3)
    assert 0 <= report.t_max <= 1
    assert 0 <= report.t_avg <= 1

# -----------------------------
# Linkage attack tests
# -----------------------------
def test_linkage_attack_unique_and_multiple(simple_df):
    """Test simulate_linkage_attack for unique, multiple, and none matches."""
    aux = pd.DataFrame({
        "age_band": ["20-29", "30-39", "30-39", "99-99"],  # last one unmatched
        "zip": ["12345", "54321", "54321", "00000"],
    })
    results = simulate_linkage_attack(simple_df, aux, ["age_band", "zip"])
    
    assert results["records_tested"] == 4
    assert results["unique"] >= 1
    assert results["multiple"] >= 1
    assert results["none"] >= 1
    assert 0 <= results["reid_probability"] <= 1

# -----------------------------
# Full report sanity test
# -----------------------------
def test_full_report_structure(simple_df):
    """Check that full_report returns expected keys and structure."""
    v = AnonymisationValidator(simple_df)
    report = v.full_report(
        qi_cols=["age_band", "zip"],
        sensitive_col="disease",
        k_required=2,
        l_required=2,
        t_required=0.5,
        numeric_bins=5
    )
    for key in ["k_anonymity", "l_diversity", "t_closeness", "risk_flags", "behaviour_patterns"]:
        assert key in report
    assert isinstance(report["behaviour_patterns"], dict)

# -----------------------------
# New robust tests
# -----------------------------
def test_full_report_linkage_attack_flag(simple_df):
    """Ensure linkage attack simulation and re-identification flagging works."""
    v = AnonymisationValidator(simple_df)
    aux_df = pd.DataFrame({
        "age_band": ["20-29", "30-39", "30-39", "99-99"],
        "zip": ["12345", "54321", "54321", "00000"],
    })
    reid_required = 0.0
    report = v.full_report(
        qi_cols=["age_band", "zip"],
        sensitive_col="disease",
        k_required=1,
        l_required=1,
        t_required=1.0,
        external_df=aux_df,
        reid_required=reid_required,
        numeric_bins=5
    )
    attack = report.get("attack_simulation", {})
    assert attack
    flags = report["risk_flags"]
    assert any("Re-identification probability" in f for f in flags)

def test_entropy_effective_l_vs_distinct(simple_df):
    """Ensure effective-l from entropy is aligned with distinct l-diversity."""
    v = AnonymisationValidator(simple_df)
    l_distinct = v.l_diversity(["age_band", "zip"], "disease", method="distinct")
    l_entropy = v.l_diversity(["age_band", "zip"], "disease", method="entropy")
    assert l_entropy.entropy_effective_min <= l_distinct.l_min
    assert l_entropy.entropy_effective_avg <= l_distinct.l_avg

def test_rare_combinations_behavior(simple_df):
    """Ensure rare combinations are detected and reported."""
    v = AnonymisationValidator(simple_df)
    report = v.full_report(
        qi_cols=["age_band", "zip"],
        sensitive_col="disease",
        k_required=1,
        l_required=1,
        t_required=1.0,
        numeric_bins=5,
        rare_threshold=2
    )
    rare_combos = report["behaviour_patterns"]["rare_combinations"]
    for rc in rare_combos:
        assert rc["count"] <= 2

def test_sensitive_skew_detection(simple_df):
    """Ensure dominant sensitive values are detected in behaviour_patterns."""
    v = AnonymisationValidator(simple_df)
    report = v.full_report(
        qi_cols=["age_band", "zip"],
        sensitive_col="disease",
        dominance_threshold=0.5,
        numeric_bins=5
    )
    skew_flags = report["behaviour_patterns"]["sensitive_skew"]
    for flag in skew_flags:
        assert flag["frequency"] > 0.5

def test_numeric_qi_sensitive_correlation(simple_df):
    """Ensure numeric QIs with numeric sensitive attribute correctly compute Pearson correlation."""
    v = AnonymisationValidator(simple_df)
    report = v.full_report(
        qi_cols=["income"],
        sensitive_col="income",
        numeric_bins=5
    )
    correlations = report["behaviour_patterns"]["qi_sensitive_correlation"]
    for corr in correlations:
        assert -1 <= corr["correlation"] <= 1

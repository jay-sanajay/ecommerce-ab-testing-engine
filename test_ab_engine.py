"""
test_ab_engine.py
Unit tests verifying the statistical engine calculations.
Author: jay-sanajay (https://github.com/jay-sanajay)
Repository: https://github.com/jay-sanajay/ecommerce-ab-testing-engine
"""

import pytest
import numpy as np
import pandas as pd
from ab_engine import (
    calculate_sample_size,
    check_sample_ratio_mismatch,
    winsorize_series,
    run_proportion_ztest,
    run_continuous_tests,
    evaluate_business_impact
)

def test_sample_size_calculator():
    res = calculate_sample_size(baseline_cvr=0.03, mde_relative=0.10, alpha=0.05, power=0.80)
    assert res["sample_size_per_variant"] > 10000
    assert res["total_required_sample"] == res["sample_size_per_variant"] * 2
    assert res["estimated_duration_days"] > 0

def test_srm_check_balanced():
    # 50,000 vs 50,000 -> Perfect split
    res = check_sample_ratio_mismatch(50000, 50000)
    assert not res["srm_detected"]
    assert res["p_value"] > 0.05

def test_srm_check_mismatch():
    # Severe mismatch: 52,000 vs 48,000
    res = check_sample_ratio_mismatch(52000, 48000)
    assert res["srm_detected"]
    assert res["p_value"] < 0.001

def test_winsorization():
    data = pd.Series([10, 20, 30, 40, 50, 1000])
    winsorized = winsorize_series(data, percentile=90)
    assert winsorized.max() < 1000

def test_proportion_ztest_significant():
    # 300 / 10000 (3.0%) vs 400 / 10000 (4.0%)
    res = run_proportion_ztest(300, 10000, 400, 10000)
    assert res["statistically_significant"]
    assert res["relative_lift_pct"] > 30.0
    assert res["p_value"] < 0.05

def test_proportion_ztest_not_significant():
    # 300 / 10000 vs 305 / 10000
    res = run_proportion_ztest(300, 10000, 305, 10000)
    assert not res["statistically_significant"]
    assert res["p_value"] > 0.05

def test_continuous_welch_and_bootstrap():
    np.random.seed(42)
    c = np.random.normal(100, 15, size=500)
    t = np.random.normal(110, 15, size=500)
    res = run_continuous_tests(c, t, n_bootstraps=200)
    assert res["statistically_significant"]
    assert res["bootstrap_ci_lower"] > 0
    assert res["bootstrap_ci_upper"] > res["bootstrap_ci_lower"]

def test_business_impact_launch():
    cvr = {"statistically_significant": True, "relative_lift_pct": 12.0, "control_rate": 0.03, "treatment_rate": 0.0336}
    aov = {"control_mean": 1000.0, "treatment_mean": 1100.0}
    srm = {"srm_detected": False}
    res = evaluate_business_impact(cvr, aov, srm, annual_pdp_visitors=1000000)
    assert res["decision"] == "LAUNCH (100% ROLLOUT)"
    assert res["projected_annual_incremental_gmv_inr"] > 0

if __name__ == "__main__":
    print("Running A/B Engine Unit Tests...")
    test_sample_size_calculator()
    print("[PASS] test_sample_size_calculator")
    test_srm_check_balanced()
    print("[PASS] test_srm_check_balanced")
    test_srm_check_mismatch()
    print("[PASS] test_srm_check_mismatch")
    test_winsorization()
    print("[PASS] test_winsorization")
    test_proportion_ztest_significant()
    print("[PASS] test_proportion_ztest_significant")
    test_proportion_ztest_not_significant()
    print("[PASS] test_proportion_ztest_not_significant")
    test_continuous_welch_and_bootstrap()
    print("[PASS] test_continuous_welch_and_bootstrap")
    test_business_impact_launch()
    print("[PASS] test_business_impact_launch")
    print("\nALL 8 STATISTICAL UNIT TESTS PASSED SUCCESSFULLY!")


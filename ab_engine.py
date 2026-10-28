"""
ab_engine.py
Core Statistical & Experimentation Engine for E-Commerce A/B Testing.
Author: jay-sanajay (https://github.com/jay-sanajay)
Repository: https://github.com/jay-sanajay/ecommerce-ab-testing-engine

Implements:
1. Power & Sample Size Calculator (Pre-experiment planning)
2. Sample Ratio Mismatch (SRM) Test (Chi-Square Goodness-of-Fit)
3. Outlier Winsorization for Financial Metrics
4. Two-Proportion Z-Test & Confidence Intervals
5. Welch's t-Test & Non-Parametric Bootstrapping for AOV / ARPU
6. Step-by-Step Funnel Drop-off Analysis
7. Heterogeneous Treatment Effects (Segment Drilldown)
8. Business Decision & Annualized GMV Projection
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, Tuple, Optional

# ==============================================================================
# 1. PRE-EXPERIMENT: POWER & SAMPLE SIZE CALCULATOR
# ==============================================================================
def calculate_sample_size(
    baseline_cvr: float = 0.032,
    mde_relative: float = 0.05,
    alpha: float = 0.05,
    power: float = 0.80,
    daily_traffic: int = 15000
) -> Dict[str, Any]:
    """
    Computes minimum required sample size per variant for two-proportion comparison.
    Formula: Fleiss with continuity / standard pooled standard error.
    """
    p1 = baseline_cvr
    p2 = baseline_cvr * (1.0 + mde_relative)
    p_pool = (p1 + p2) / 2.0
    
    z_alpha = stats.norm.ppf(1 - alpha / 2.0)
    z_beta = stats.norm.ppf(power)
    
    numerator = (z_alpha * np.sqrt(2 * p_pool * (1 - p_pool)) + 
                 z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    denominator = (p2 - p1) ** 2
    
    n_per_variant = int(np.ceil(numerator / denominator))
    total_sample = n_per_variant * 2
    estimated_days = int(np.ceil(total_sample / daily_traffic))
    
    return {
        "baseline_cvr": p1,
        "target_cvr": p2,
        "mde_relative": mde_relative,
        "alpha": alpha,
        "power": power,
        "sample_size_per_variant": n_per_variant,
        "total_required_sample": total_sample,
        "daily_traffic": daily_traffic,
        "estimated_duration_days": estimated_days
    }


# ==============================================================================
# 2. GUARDRAIL CHECKS: SAMPLE RATIO MISMATCH (SRM)
# ==============================================================================
def check_sample_ratio_mismatch(
    control_count: int,
    treatment_count: int,
    expected_ratio: float = 0.50,
    p_threshold: float = 0.01
) -> Dict[str, Any]:
    """
    Performs Pearson's Chi-Square Goodness-of-Fit test to verify traffic split integrity.
    If p-value < 0.01, there is evidence of Sample Ratio Mismatch (SRM), invalidating the test.
    """
    total = control_count + treatment_count
    expected = [total * expected_ratio, total * (1.0 - expected_ratio)]
    observed = [control_count, treatment_count]
    
    chi2_stat, p_val = stats.chisquare(f_obs=observed, f_exp=expected)
    srm_flag = bool(p_val < p_threshold)
    
    return {
        "control_count": control_count,
        "treatment_count": treatment_count,
        "observed_ratio": round(treatment_count / total, 4),
        "expected_ratio": expected_ratio,
        "chi2_stat": round(float(chi2_stat), 4),
        "p_value": float(p_val),
        "srm_detected": srm_flag,
        "status": "FAIL: Sample Ratio Mismatch Detected! Guardrail violated." if srm_flag else "PASS: Split ratio is statistically sound."
    }


# ==============================================================================
# 3. OUTLIER HANDLING: WINSORIZATION
# ==============================================================================
def winsorize_series(series: pd.Series, percentile: float = 99.0) -> pd.Series:
    """
    Capping extreme values at the specified percentile to reduce variance from bulk wholesale buyers.
    """
    cutoff = np.percentile(series.dropna(), percentile)
    return series.clip(upper=cutoff)


# ==============================================================================
# 4. HYPOTHESIS TESTING: BINARY METRIC (TWO-PROPORTION Z-TEST)
# ==============================================================================
def run_proportion_ztest(
    count_c: int, nobs_c: int,
    count_t: int, nobs_t: int,
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Computes two-tailed pooled Z-test for proportions and 95% Confidence Interval.
    """
    p_c = count_c / nobs_c if nobs_c > 0 else 0.0
    p_t = count_t / nobs_t if nobs_t > 0 else 0.0
    
    # Pooled probability
    p_pool = (count_c + count_t) / (nobs_c + nobs_t)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / nobs_c + 1 / nobs_t))
    
    z_stat = (p_t - p_c) / se_pool if se_pool > 0 else 0.0
    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(z_stat)))
    
    # Unpooled Standard Error for Confidence Interval of Difference
    se_diff = np.sqrt((p_c * (1 - p_c) / nobs_c) + (p_t * (1 - p_t) / nobs_t))
    z_crit = stats.norm.ppf(1.0 - alpha / 2.0)
    
    abs_diff = p_t - p_c
    ci_lower = abs_diff - z_crit * se_diff
    ci_upper = abs_diff + z_crit * se_diff
    
    relative_lift = ((p_t - p_c) / p_c) * 100.0 if p_c > 0 else 0.0
    
    return {
        "control_rate": float(p_c),
        "treatment_rate": float(p_t),
        "absolute_diff": float(abs_diff),
        "relative_lift_pct": float(relative_lift),
        "z_statistic": float(z_stat),
        "p_value": float(p_value),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "statistically_significant": bool(p_value < alpha)
    }


# ==============================================================================
# 5. CONTINUOUS METRIC TESTING: WELCH'S T-TEST & BOOTSTRAPPING
# ==============================================================================
def run_continuous_tests(
    vals_c: np.ndarray,
    vals_t: np.ndarray,
    metric_name: str = "AOV",
    alpha: float = 0.05,
    n_bootstraps: int = 1000,
    random_seed: int = 42
) -> Dict[str, Any]:
    """
    Performs Welch's t-test (unequal variance) and non-parametric Bootstrapping for continuous metrics.
    """
    mean_c = float(np.mean(vals_c))
    mean_t = float(np.mean(vals_t))
    abs_diff = mean_t - mean_c
    rel_lift = (abs_diff / mean_c) * 100.0 if mean_c > 0 else 0.0
    
    # Welch's t-test
    t_stat, p_val = stats.ttest_ind(vals_t, vals_c, equal_var=False)
    
    # Bootstrapping for non-normal empirical CI
    np.random.seed(random_seed)
    boot_diffs = []
    len_c, len_t = len(vals_c), len(vals_t)
    for _ in range(n_bootstraps):
        sample_c = np.random.choice(vals_c, size=len_c, replace=True)
        sample_t = np.random.choice(vals_t, size=len_t, replace=True)
        boot_diffs.append(np.mean(sample_t) - np.mean(sample_c))
    
    boot_diffs = np.array(boot_diffs)
    ci_lower = float(np.percentile(boot_diffs, 100 * (alpha / 2.0)))
    ci_upper = float(np.percentile(boot_diffs, 100 * (1 - alpha / 2.0)))
    
    return {
        "metric": metric_name,
        "control_mean": mean_c,
        "treatment_mean": mean_t,
        "absolute_diff": abs_diff,
        "relative_lift_pct": rel_lift,
        "t_statistic": float(t_stat),
        "p_value": float(p_val),
        "bootstrap_ci_lower": ci_lower,
        "bootstrap_ci_upper": ci_upper,
        "statistically_significant": bool(p_val < alpha),
        "bootstrap_samples": boot_diffs
    }


# ==============================================================================
# 6. FUNNEL DROP-OFF ANALYSIS
# ==============================================================================
def analyze_funnel(funnel_df: pd.DataFrame, users_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates conversion rate at each step of the e-commerce purchase funnel:
    Step 0: PDP View -> Step 1: Add to Cart -> Step 2: Checkout Started -> Step 3: Purchase
    """
    merged = funnel_df.merge(users_df[["user_id", "variant"]], on="user_id", how="left")
    
    steps = ["pdp_view", "add_to_cart", "checkout_started", "purchase"]
    summary = []
    
    for variant in ["Control", "Treatment"]:
        v_df = merged[merged["variant"] == variant]
        total_pdp = v_df[v_df["event_type"] == "pdp_view"]["user_id"].nunique()
        total_cart = v_df[v_df["event_type"] == "add_to_cart"]["user_id"].nunique()
        total_checkout = v_df[v_df["event_type"] == "checkout_started"]["user_id"].nunique()
        total_purchase = v_df[v_df["event_type"] == "purchase"]["user_id"].nunique()
        
        summary.append({
            "variant": variant,
            "pdp_views": total_pdp,
            "add_to_cart": total_cart,
            "cart_rate_pct": (total_cart / total_pdp) * 100.0,
            "checkout_started": total_checkout,
            "cart_to_checkout_pct": (total_checkout / total_cart) * 100.0,
            "purchases": total_purchase,
            "checkout_to_purchase_pct": (total_purchase / total_checkout) * 100.0,
            "overall_cvr_pct": (total_purchase / total_pdp) * 100.0
        })
        
    return pd.DataFrame(summary)


# ==============================================================================
# 7. SUBGROUP / HETEROGENEOUS TREATMENT EFFECTS
# ==============================================================================
def analyze_subgroups(users_df: pd.DataFrame, orders_df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """
    Evaluates whether the treatment effect varies significantly across customer segments
    (e.g., Device, City Tier, User Type, Category).
    """
    results = []
    order_user_set = set(orders_df["user_id"])
    
    for val, group in users_df.groupby(dimension):
        ctrl = group[group["variant"] == "Control"]
        trt = group[group["variant"] == "Treatment"]
        
        n_ctrl = len(ctrl)
        n_trt = len(trt)
        
        purchases_ctrl = ctrl["user_id"].isin(order_user_set).sum()
        purchases_trt = trt["user_id"].isin(order_user_set).sum()
        
        test_res = run_proportion_ztest(purchases_ctrl, n_ctrl, purchases_trt, n_trt)
        
        results.append({
            dimension: val,
            "control_users": n_ctrl,
            "control_cvr": round(test_res["control_rate"] * 100, 2),
            "treatment_users": n_trt,
            "treatment_cvr": round(test_res["treatment_rate"] * 100, 2),
            "relative_lift_pct": round(test_res["relative_lift_pct"], 2),
            "p_value": round(test_res["p_value"], 5),
            "significant": test_res["statistically_significant"]
        })
        
    return pd.DataFrame(results)


# ==============================================================================
# 8. BUSINESS IMPACT & ROLLOUT RECOMMENDATION
# ==============================================================================
def evaluate_business_impact(
    cvr_results: Dict[str, Any],
    aov_results: Dict[str, Any],
    srm_results: Dict[str, Any],
    annual_pdp_visitors: int = 12000000
) -> Dict[str, Any]:
    """
    Synthesizes statistical results into an executive recommendation with projected annual GMV impact.
    """
    if srm_results["srm_detected"]:
        decision = "STOP & RE-RUN"
        reason = "Sample Ratio Mismatch detected. Traffic routing is biased; results cannot be trusted."
        incremental_gmv = 0.0
    elif cvr_results["statistically_significant"] and cvr_results["relative_lift_pct"] > 0:
        decision = "LAUNCH (100% ROLLOUT)"
        reason = "Statistically significant improvement in conversion and basket size with zero guardrail violations."
        
        # Incremental GMV calculation:
        # Control Revenue Per User (ARPU) = CVR_c * AOV_c
        # Treatment ARPU = CVR_t * AOV_t
        arpu_c = cvr_results["control_rate"] * aov_results["control_mean"]
        arpu_t = cvr_results["treatment_rate"] * aov_results["treatment_mean"]
        delta_arpu = arpu_t - arpu_c
        incremental_gmv = annual_pdp_visitors * delta_arpu
    else:
        decision = "DO NOT LAUNCH"
        reason = "Treatment did not achieve statistically significant positive lift."
        incremental_gmv = 0.0
        
    return {
        "decision": decision,
        "reason": reason,
        "annual_pdp_traffic_assumed": annual_pdp_visitors,
        "control_arpu": cvr_results["control_rate"] * aov_results["control_mean"],
        "treatment_arpu": cvr_results["treatment_rate"] * aov_results["treatment_mean"],
        "incremental_arpu_per_user": (cvr_results["treatment_rate"] * aov_results["treatment_mean"]) - (cvr_results["control_rate"] * aov_results["control_mean"]),
        "projected_annual_incremental_gmv_inr": incremental_gmv,
        "projected_annual_incremental_gmv_crores": incremental_gmv / 1e7
    }

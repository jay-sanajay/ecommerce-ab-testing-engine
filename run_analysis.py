"""
run_analysis.py
Executes the end-to-end Nykaa A/B testing analysis.
Author: jay-sanajay (https://github.com/jay-sanajay)
Repository: https://github.com/jay-sanajay/ecommerce-ab-testing-engine

Performs data loading, statistical hypothesis tests, bootstrapping, visual generation,
and prints an executive-grade summary report.
"""

import os
import json
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from ab_engine import (
    calculate_sample_size,
    check_sample_ratio_mismatch,
    winsorize_series,
    run_proportion_ztest,
    run_continuous_tests,
    analyze_funnel,
    analyze_subgroups,
    evaluate_business_impact
)
from generate_data import generate_experiment_data

def run_pipeline():
    print("=" * 80)
    print("      NYKAA PRODUCT EXPERIMENTATION ENGINE: END-TO-END ANALYSIS")
    print("  Feature: 'Complete Your Routine' Bundles vs Control Carousel on PDP")
    print("=" * 80)

    # 1. Data check or generation
    db_path = os.path.join("data", "nykaa_experiment.db")
    if not os.path.exists(db_path):
        print("Experiment database not found. Generating fresh data...")
        users_df, funnel_df, orders_df = generate_experiment_data(num_users=100000)
    else:
        print(f"Loading existing experiment database from {db_path}...")
        conn = sqlite3.connect(db_path)
        users_df = pd.read_sql("SELECT * FROM users", conn)
        funnel_df = pd.read_sql("SELECT * FROM funnel_events", conn)
        orders_df = pd.read_sql("SELECT * FROM orders", conn)
        conn.close()

    # 2. Pre-experiment power planning context
    power_plan = calculate_sample_size(baseline_cvr=0.032, mde_relative=0.05, daily_traffic=12000)
    print("\n--- [STAGE 1] PRE-EXPERIMENT DESIGN & POWER PLANNING ---")
    print(f"  Baseline CVR:          {power_plan['baseline_cvr'] * 100:.2f}%")
    print(f"  Target Relative MDE:   {power_plan['mde_relative'] * 100:.1f}%")
    print(f"  Req. Sample / Variant: {power_plan['sample_size_per_variant']:,}")
    print(f"  Total Sample Needed:   {power_plan['total_required_sample']:,}")
    print(f"  Est. Experiment Days:  {power_plan['estimated_duration_days']} days (@ 12k daily traffic)")

    # 3. Guardrail: SRM Check
    ctrl_users = len(users_df[users_df["variant"] == "Control"])
    trt_users = len(users_df[users_df["variant"] == "Treatment"])
    srm = check_sample_ratio_mismatch(ctrl_users, trt_users)
    print("\n--- [STAGE 2] TRAFFIC GUARDRAILS & SRM INTEGRITY ---")
    print(f"  Control Users:         {srm['control_count']:,} ({srm['control_count']/(ctrl_users+trt_users)*100:.2f}%)")
    print(f"  Treatment Users:       {srm['treatment_count']:,} ({srm['treatment_count']/(ctrl_users+trt_users)*100:.2f}%)")
    print(f"  Chi-Square Stat:       {srm['chi2_stat']}")
    print(f"  p-value:               {srm['p_value']:.4f}")
    print(f"  SRM Status:            {srm['status']}")

    # 4. Purchase Conversion Rate (Two-Proportion Z-Test)
    order_user_set = set(orders_df["user_id"])
    ctrl_purchasers = users_df[users_df["variant"] == "Control"]["user_id"].isin(order_user_set).sum()
    trt_purchasers = users_df[users_df["variant"] == "Treatment"]["user_id"].isin(order_user_set).sum()

    cvr_test = run_proportion_ztest(ctrl_purchasers, ctrl_users, trt_purchasers, trt_users)
    print("\n--- [STAGE 3] PRIMARY CONVERSION RATE (PDP -> PURCHASE) ---")
    print(f"  Control Conversion:    {cvr_test['control_rate'] * 100:.2f}% ({ctrl_purchasers:,} / {ctrl_users:,})")
    print(f"  Treatment Conversion:  {cvr_test['treatment_rate'] * 100:.2f}% ({trt_purchasers:,} / {trt_users:,})")
    print(f"  Absolute Difference:   +{cvr_test['absolute_diff'] * 100:.2f}% pts")
    print(f"  Relative Uplift:       +{cvr_test['relative_lift_pct']:.2f}%")
    print(f"  95% Conf. Interval:    [{cvr_test['ci_lower']*100:.2f}%, {cvr_test['ci_upper']*100:.2f}%]")
    print(f"  Z-Statistic:           {cvr_test['z_statistic']:.3f} (p = {cvr_test['p_value']:.4e})")
    print(f"  Significance (alpha=0.05): {'YES (Significant Lift)' if cvr_test['statistically_significant'] else 'NO'}")

    # 5. Continuous Financial Metric: AOV & Outlier Winsorization
    orders_df["order_value_winsorized"] = winsorize_series(orders_df["order_value"], percentile=99.0)
    
    aov_ctrl = orders_df[orders_df["variant"] == "Control"]["order_value_winsorized"].values
    aov_trt = orders_df[orders_df["variant"] == "Treatment"]["order_value_winsorized"].values

    aov_test = run_continuous_tests(aov_ctrl, aov_trt, metric_name="AOV (INR)")
    print("\n--- [STAGE 4] BASKET SIZE & AVERAGE ORDER VALUE (AOV) ---")
    print(f"  Control AOV:           INR {aov_test['control_mean']:.2f}")
    print(f"  Treatment AOV:         INR {aov_test['treatment_mean']:.2f}")
    print(f"  Absolute AOV Lift:     +INR {aov_test['absolute_diff']:.2f}")
    print(f"  Relative AOV Uplift:   +{aov_test['relative_lift_pct']:.2f}%")
    print(f"  Welch's t-statistic:   {aov_test['t_statistic']:.3f} (p = {aov_test['p_value']:.4e})")
    print(f"  Bootstrap 95% CI:      [+INR {aov_test['bootstrap_ci_lower']:.2f}, +INR {aov_test['bootstrap_ci_upper']:.2f}]")

    # 6. Step-by-Step Funnel Analysis
    funnel_summary = analyze_funnel(funnel_df, users_df)
    print("\n--- [STAGE 5] FULL-FUNNEL DROP-OFF BREAKDOWN ---")
    print(funnel_summary.to_string(index=False))

    # 7. Subgroup Heterogeneity (Device & User Type)
    device_breakdown = analyze_subgroups(users_df, orders_df, "device")
    user_type_breakdown = analyze_subgroups(users_df, orders_df, "user_type")
    print("\n--- [STAGE 6] HETEROGENEOUS TREATMENT EFFECTS (BY DEVICE) ---")
    print(device_breakdown.to_string(index=False))

    # 8. Business Decision & Incremental Annual GMV
    business_impact = evaluate_business_impact(cvr_test, aov_test, srm, annual_pdp_visitors=15000000)
    print("\n--- [STAGE 7] EXECUTIVE DECISION & REVENUE PROJECTION ---")
    print(f"  Final Decision:        {business_impact['decision']}")
    print(f"  Executive Rationale:   {business_impact['reason']}")
    print(f"  Control ARPU:          INR {business_impact['control_arpu']:.2f}")
    print(f"  Treatment ARPU:        INR {business_impact['treatment_arpu']:.2f}")
    print(f"  Incremental ARPU/user: +INR {business_impact['incremental_arpu_per_user']:.2f}")
    print(f"  Projected Annual GMV:  +INR {business_impact['projected_annual_incremental_gmv_crores']:.2f} Crores INR")
    print("=" * 80)

    # 9. Generate Charts
    os.makedirs("reports/figures", exist_ok=True)
    sns.set_theme(style="whitegrid")

    # Figure 1: Funnel Comparison
    plt.figure(figsize=(10, 5))
    funnel_stages = ["PDP View", "Add to Cart", "Checkout Started", "Purchase"]
    c_counts = [
        funnel_summary[funnel_summary["variant"]=="Control"]["pdp_views"].values[0],
        funnel_summary[funnel_summary["variant"]=="Control"]["add_to_cart"].values[0],
        funnel_summary[funnel_summary["variant"]=="Control"]["checkout_started"].values[0],
        funnel_summary[funnel_summary["variant"]=="Control"]["purchases"].values[0]
    ]
    t_counts = [
        funnel_summary[funnel_summary["variant"]=="Treatment"]["pdp_views"].values[0],
        funnel_summary[funnel_summary["variant"]=="Treatment"]["add_to_cart"].values[0],
        funnel_summary[funnel_summary["variant"]=="Treatment"]["checkout_started"].values[0],
        funnel_summary[funnel_summary["variant"]=="Treatment"]["purchases"].values[0]
    ]
    
    x = np.arange(len(funnel_stages))
    width = 0.35
    plt.bar(x - width/2, c_counts, width, label='Control (Carousel)', color='#94a3b8')
    plt.bar(x + width/2, t_counts, width, label='Treatment (Routine Bundle)', color='#e11d48')
    plt.ylabel('Unique Users')
    plt.title('Nykaa E-Commerce Funnel: Control vs Treatment', fontsize=14, fontweight='bold')
    plt.xticks(x, funnel_stages)
    plt.legend()
    plt.tight_layout()
    plt.savefig("reports/figures/funnel_comparison.png", dpi=150)
    plt.close()

    # Figure 2: Bootstrapped AOV Difference Distribution
    plt.figure(figsize=(8, 4.5))
    sns.histplot(aov_test["bootstrap_samples"], kde=True, color="#e11d48", bins=30)
    plt.axvline(aov_test["bootstrap_ci_lower"], color='black', linestyle='--', label=f'95% CI Lower (+INR {aov_test["bootstrap_ci_lower"]:.1f})')
    plt.axvline(aov_test["bootstrap_ci_upper"], color='black', linestyle='--', label=f'95% CI Upper (+INR {aov_test["bootstrap_ci_upper"]:.1f})')
    plt.axvline(aov_test["absolute_diff"], color='#881337', linewidth=2.5, label=f'Observed Delta (+INR {aov_test["absolute_diff"]:.1f})')
    plt.title('Bootstrapped Distribution of AOV Difference (1,000 Iterations)', fontsize=12, fontweight='bold')
    plt.xlabel('Mean AOV Difference (INR)')
    plt.ylabel('Bootstrap Frequency')
    plt.legend()
    plt.tight_layout()
    plt.savefig("reports/figures/bootstrap_aov_distribution.png", dpi=150)
    plt.close()

    # Figure 3: Segment Uplift by Device
    plt.figure(figsize=(8, 4))
    sns.barplot(data=device_breakdown, x="device", y="relative_lift_pct", palette="magma")
    plt.axhline(0, color='gray', linestyle='--')
    plt.title('Conversion Uplift by Device Segment (%)', fontsize=12, fontweight='bold')
    plt.ylabel('Relative Conversion Lift (%)')
    plt.xlabel('User Device')
    for idx, row in device_breakdown.iterrows():
        plt.text(idx, row["relative_lift_pct"] + 0.5, f"+{row['relative_lift_pct']:.1f}%", ha='center', fontweight='bold')
    plt.tight_layout()
    plt.savefig("reports/figures/subgroup_lift_device.png", dpi=150)
    plt.close()

    print("\nVisual reports saved to reports/figures/:")
    print(" - reports/figures/funnel_comparison.png")
    print(" - reports/figures/bootstrap_aov_distribution.png")
    print(" - reports/figures/subgroup_lift_device.png")

    return {
        "power_plan": power_plan,
        "srm": srm,
        "cvr_test": cvr_test,
        "aov_test": {k: v for k, v in aov_test.items() if k != "bootstrap_samples"},
        "business_impact": business_impact
    }

if __name__ == "__main__":
    run_pipeline()

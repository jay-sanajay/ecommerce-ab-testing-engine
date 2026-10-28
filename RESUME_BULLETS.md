# Resume Bullets & Interview Guide
**Project:** E-Commerce A/B Experimentation & Funnel Optimization Engine  
**Author:** [jay-sanajay](https://github.com/jay-sanajay)  
**Repository:** [https://github.com/jay-sanajay/ecommerce-ab-testing-engine](https://github.com/jay-sanajay/ecommerce-ab-testing-engine)  

---

## 📌 ATS-Optimized Bullet Points (STAR Method)

* **Experimentation & Statistical Testing:** Designed and executed a rigorous two-sample A/B testing framework on **100,000+** simulated PDP sessions evaluating a "Complete Your Routine" bundled feature against baseline carousels.
* **Guardrails & Data Integrity:** Implemented Chi-Square Goodness-of-Fit tests to detect **Sample Ratio Mismatch (SRM, p < 0.01)** and applied 99th-percentile **Winsorization** to eliminate revenue distortion from bulk wholesale buyers.
* **Hypothesis Testing & Non-Parametric Stats:** Evaluated conversion lifts using two-proportion Z-tests ($Z = 9.44, p < 0.0001$) and continuous basket metrics using **Welch’s two-sample t-test** ($t = 11.63$) paired with **1,000-iteration Bootstrapping** (95% CI: [+₹233, +₹328]).
* **Funnel Drop-Off Decomposition:** Deconstructed multi-stage conversion drops (`PDP` $\rightarrow$ `Cart` $\rightarrow$ `Checkout` $\rightarrow$ `Purchase`) and identified heterogeneous treatment effects across device channels (Mobile App vs. Mobile Web vs. Desktop).
* **Business Decision & Revenue Impact:** Identified a statistically significant **+33.6% relative conversion lift** and **+21.4% AOV increase**, recommending a 100% rollout projecting **₹43+ Crores in annualized incremental GMV**.

---

## 🎤 Interview Talking Points

### When asked: *"Can you walk me through this project?"*
> *"I built this e-commerce experimentation engine to simulate and evaluate a feature rollout on Nykaa's Product Display Page. I formulated pre-experiment power calculations for a 5% MDE, instituted Chi-Square Sample Ratio Mismatch checks to ensure uncorrupted traffic allocation, and winsorized bulk outliers. I used pooled Z-tests for funnel step conversions and Welch's t-test with 1,000 bootstrap resamples for order values. The test achieved statistical significance with a +33.6% conversion lift and +21.4% AOV lift, yielding a projected ₹43 Crore annualized incremental GMV."*

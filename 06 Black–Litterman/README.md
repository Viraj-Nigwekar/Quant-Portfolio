# Black–Litterman Model (Reference Implementation)

This folder contains a clean, step-by-step implementation of the **Black–Litterman
portfolio model**. The goal is to provide a transparent, reproducible version of
the core BL methodology, built from first principles and organized across three
notebooks.

The implementation follows the canonical structure:

1. **Equilibrium prior** (implied returns)
2. **Investor views** (encoded in linear form)
3. **Posterior expected returns** (Bayesian update combining prior + views)

No optimization or backtesting is performed here; the focus is on the inputs and
expected-return mechanics that characterize the BL framework.

---

## Notebook Structure

### **01_Equilibrium_Prior.ipynb**
Builds the Black–Litterman **prior**:
- downloads price data
- computes log returns and the annualized covariance matrix  
- defines a market portfolio (equal-weight proxy)  
- computes implied equilibrium excess returns  
  \[
  \pi = \lambda \Sigma w_{mkt}
  \]

This gives the neutral starting point that BL uses before incorporating any
investor views.

---

### **02_Views_and_Confidence.ipynb**
Defines investor views in BL form:
- absolute view on AAPL  
- relative view: MSFT vs META  
- constructs the **P** matrix (view loadings)  
- constructs the **Q** vector (view targets)  
- builds the **Ω** matrix (view uncertainty / confidence)

This notebook does not perform any updating; it only encodes the views in the
required mathematical structure.

---

### **03_Black_Litterman_Posterior.ipynb**
Combines the prior and the views to compute **posterior expected returns** using:

\[
\mu_{BL} =
\Big( (\tau \Sigma)^{-1} + P^T \Omega^{-1} P \Big)^{-1}
\Big( (\tau \Sigma)^{-1} \pi + P^T \Omega^{-1} Q \Big)
\]

Outputs include:
- posterior expected return vector  
- comparison plot of prior vs posterior  
- brief interpretation of how the views shift the equilibrium prior

---

## Notes on Development Workflow

All code and logic in these notebooks were written by me.  
AI tools (ChatGPT) were used **only for polishing text, helping with structure,
and assisting with documentation and comments**.  
No auto-generated code or libraries were used; the math, implementation steps,
and final code logic reflect my own work and understanding.

This approach keeps the learning process authentic while still benefiting from
clarity and improved readability in the final notebooks.

---

## Purpose of This Folder

This is a **reference-grade implementation** of the Black–Litterman model.  
It is not designed for performance claims or portfolio recommendations.  
The goal is conceptual clarity, correct mechanics, and a foundation that can be
extended into allocation, optimization, or backtesting in later modules.

---

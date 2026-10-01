"""Generate a fake dataset with the same columns as Criteo Uplift v2.1.

The rates are calibrated to roughly match the published dataset:
85/15 treatment split, ~3.6% of treated users exposed, visits ~3.8% (control)
vs ~4.9% (treatment), conversions ~0.19% vs ~0.31%. Two properties of the real
data are built in on purpose because later steps depend on them:

* Exposure is not random: users with a high latent "activity" score are more
  likely to see the ad AND more likely to visit/convert anyway.
* The ad only works through exposure, and works more for some users than others
  (heterogeneous effect driven by f2), so uplift models have something to find.

These numbers are made up. Never report them as findings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit

from abkit.data import FEATURES

TREATMENT_SHARE = 0.85
TARGETS = {
    "exposure_given_treatment": 0.036,
    "visit_control": 0.038,
    "visit_treatment": 0.0485,
    "conversion_control": 0.0019,
    "conversion_treatment": 0.0031,
}


def _features(z: np.ndarray, rng: np.random.Generator) -> pd.DataFrame:
    """Turn latent normals into 12 anonymized-looking features (some skewed, some discrete)."""
    n = z.shape[0]
    cols = {}
    for i, name in enumerate(FEATURES):
        x = z[:, i]
        if i % 4 == 1:
            x = np.exp(0.5 * x)  # right-skewed
        elif i % 4 == 3:
            x = np.round(x * 2) / 2  # coarse / discrete
        cols[name] = (10 * (i + 1) + 3 * x + 0.05 * rng.standard_normal(n)).astype("float32")
    return pd.DataFrame(cols)


def generate(n_rows: int = 2_000_000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_rows, len(FEATURES)))

    weights = np.array([0.6, 0.4, 0.0, 0.3, -0.3, 0.2, 0.0, 0.0, 0.25, 0.0, -0.2, 0.15])
    activity = z @ weights
    activity = (activity - activity.mean()) / activity.std()
    # Ad works more for users with high f2 (latent z2).
    effect_scale = 1 + 0.8 * np.tanh(z[:, 2])

    treatment = (rng.random(n_rows) < TREATMENT_SHARE).astype("int8")

    # Exposure: only treated users, more likely for active users.
    a_exp = brentq(lambda a: expit(a + 1.2 * activity).mean() - TARGETS["exposure_given_treatment"], -20, 5)
    p_exp = expit(a_exp + 1.2 * activity)

    # Visit: baseline set by control rate, ad lift (via exposure) set by treatment rate.
    def p_visit(a, b, exposed):
        return expit(a + 1.0 * activity + b * effect_scale * exposed)

    a_vis = brentq(lambda a: p_visit(a, 0, 0).mean() - TARGETS["visit_control"], -20, 5)

    def visit_treat(b):
        return (p_exp * p_visit(a_vis, b, 1) + (1 - p_exp) * p_visit(a_vis, b, 0)).mean()

    b_vis = brentq(lambda b: visit_treat(b) - TARGETS["visit_treatment"], 0, 10)

    # Conversion: only after a visit; ad also raises purchase rate among visitors.
    def p_conv(a, b, exposed):
        return expit(a + 0.8 * activity + b * effect_scale * exposed)

    a_conv = brentq(
        lambda a: (p_visit(a_vis, 0, 0) * p_conv(a, 0, 0)).mean() - TARGETS["conversion_control"], -20, 10
    )

    def conv_treat(b):
        exposed = p_exp * p_visit(a_vis, b_vis, 1) * p_conv(a_conv, b, 1)
        unexposed = (1 - p_exp) * p_visit(a_vis, b_vis, 0) * p_conv(a_conv, b, 0)
        return (exposed + unexposed).mean()

    b_conv = brentq(lambda b: conv_treat(b) - TARGETS["conversion_treatment"], 0, 10)

    exposure = (treatment * (rng.random(n_rows) < p_exp)).astype("int8")
    visit = (rng.random(n_rows) < p_visit(a_vis, b_vis, exposure)).astype("int8")
    conversion = (visit * (rng.random(n_rows) < p_conv(a_conv, b_conv, exposure))).astype("int8")

    df = _features(z, rng)
    df["treatment"] = treatment
    df["conversion"] = conversion
    df["visit"] = visit
    df["exposure"] = exposure
    return df

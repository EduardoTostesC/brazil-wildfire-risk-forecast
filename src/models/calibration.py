"""Probability calibration utilities with zero cross-version pickling fragility.

Provides:
- PlattCalibrator: 1D sigmoid scaling on log-odds (Platt, 1999) storing only
  scalar coefficients (coef_, intercept_), avoiding sklearn internal attribute
  incompatibilities (e.g., 'multi_class' attribute deprecation between 1.5 and 1.9).
- IsotonicCalibrator: Non-parametric piecewise monotonic calibration.
- compute_ece: Expected Calibration Error computation with explicit binning.
"""

from dataclasses import dataclass

import numpy as np
from scipy.special import expit, logit
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Calculate Expected Calibration Error (ECE) with uniform binning.

    ECE = sum_{m=1}^M (|B_m| / N) * |acc(B_m) - conf(B_m)|

    Args:
        y_true: Binary ground truth array (0 or 1).
        y_prob: Predicted probability array in [0, 1].
        n_bins: Number of probability bins.

    Returns:
        Scalar ECE value in [0, 1].
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    if n == 0:
        return 0.0

    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i + 1]
        mask = (y_prob >= low) & (y_prob < high) if i < n_bins - 1 else (y_prob >= low) & (y_prob <= high)
        n_in_bin = np.sum(mask)
        if n_in_bin > 0:
            bin_acc = np.mean(y_true[mask])
            bin_conf = np.mean(y_prob[mask])
            ece += (n_in_bin / n) * np.abs(bin_acc - bin_conf)

    return float(ece)


@dataclass
class PlattCalibrator:
    """Platt Scaling: 1D Logistic Sigmoid on log-odds.

    P(y=1 | z) = 1 / (1 + exp(-(coef * z + intercept)))
    where z = logit(p_raw) = ln(p_raw / (1 - p_raw)).

    Stores only raw scalar floats (coef_, intercept_) to guarantee seamless
    deserialization across any Python/scikit-learn versions without AttributeError.
    """

    coef_: float = 1.0
    intercept_: float = 0.0
    is_fitted_: bool = False
    clip_eps: float = 1e-6

    def fit(self, probs_or_logits: np.ndarray, y_true: np.ndarray, is_logit: bool = True) -> "PlattCalibrator":
        """Fit Platt scaling parameters via regularized logistic regression.

        Args:
            probs_or_logits: Log-odds (if is_logit=True, default) or raw probabilities (if is_logit=False).
            y_true: Binary ground truth labels.
            is_logit: Whether input is already logit-transformed (default True for sklearn compatibility).
        """
        y_true = np.asarray(y_true, dtype=int)
        x = np.asarray(probs_or_logits, dtype=float)

        if not is_logit:
            clipped = np.clip(x, self.clip_eps, 1.0 - self.clip_eps)
            z = logit(clipped).reshape(-1, 1)
        else:
            z = x.reshape(-1, 1)

        # Fit 1D Logistic Regression
        lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
        lr.fit(z, y_true)

        self.coef_ = float(lr.coef_[0, 0])
        self.intercept_ = float(lr.intercept_[0])
        self.is_fitted_ = True
        return self

    def predict_proba(self, probs_or_logits: np.ndarray, is_logit: bool = True) -> np.ndarray:
        """Compute calibrated probabilities.

        Args:
            probs_or_logits: Log-odds (if is_logit=True, default) or raw probabilities (if is_logit=False).
            is_logit: Whether input is already logit-transformed (default True for sklearn compatibility).

        Returns:
            2D array of shape (N, 2) matching scikit-learn predict_proba interface:
            column 0 is P(y=0), column 1 is P(y=1).
        """
        x = np.asarray(probs_or_logits, dtype=float)
        if not is_logit:
            clipped = np.clip(x, self.clip_eps, 1.0 - self.clip_eps)
            z = logit(clipped)
        else:
            z = x

        p1 = expit(self.coef_ * z + self.intercept_)
        p1 = np.clip(p1, 0.0, 1.0)
        p0 = 1.0 - p1

        return np.column_stack([p0.ravel(), p1.ravel()])

    def calibrate(self, probs: np.ndarray) -> np.ndarray:
        """Return 1D array of calibrated positive-class probabilities directly from raw probs."""
        res = self.predict_proba(probs, is_logit=False)
        return res[:, 1].ravel()

    def to_dict(self) -> dict:
        return {
            "type": "PlattCalibrator",
            "coef": self.coef_,
            "intercept": self.intercept_,
            "is_fitted": self.is_fitted_,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PlattCalibrator":
        return cls(coef_=d["coef"], intercept_=d["intercept"], is_fitted_=d.get("is_fitted", True))


class IsotonicCalibrator:
    """Non-parametric isotonic regression calibrator."""

    def __init__(self):
        self.ir = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self.is_fitted_ = False

    def fit(self, probs: np.ndarray, y_true: np.ndarray) -> "IsotonicCalibrator":
        probs = np.asarray(probs, dtype=float)
        y_true = np.asarray(y_true, dtype=float)
        self.ir.fit(probs, y_true)
        self.is_fitted_ = True
        return self

    def predict_proba(self, probs: np.ndarray) -> np.ndarray:
        probs = np.asarray(probs, dtype=float)
        p1 = np.clip(self.ir.predict(probs), 0.0, 1.0)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def calibrate(self, probs: np.ndarray) -> np.ndarray:
        res = self.predict_proba(probs)
        return res[:, 1]

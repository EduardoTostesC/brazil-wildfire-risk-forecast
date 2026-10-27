"""Paired date-block uncertainty conditional on the observed spatial domain."""

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score


def top_k_tie_sensitivity(y, probability, fraction=.10):
    """Expected and attainable Top-K counts when cutoff ties are exchangeable.

    This descriptive sensitivity leaves legacy ranking tables unchanged.
    Bounds reflect tie ordering, not statistical confidence intervals.
    """
    y, probability = np.asarray(y), np.asarray(probability, dtype=float)
    if (y.ndim != 1 or probability.shape != y.shape or not len(y)
            or not np.isin(y, [0, 1]).all() or not np.isfinite(probability).all()
            or ((probability < 0) | (probability > 1)).any() or not 0 < fraction <= 1):
        raise ValueError("Top-K requires aligned binary labels, valid probabilities and a fraction in (0, 1]")
    k = int(np.ceil(fraction * len(y)))
    cutoff = float(np.partition(probability, len(y) - k)[len(y) - k])
    above, tied = probability > cutoff, probability == cutoff
    remaining = k - int(above.sum())
    base_tp, tied_tp = int(y[above].sum()), int(y[tied].sum())
    tied_n = int(tied.sum())
    expected = base_tp + remaining * tied_tp / tied_n
    lower = base_tp + max(0, remaining - (tied_n - tied_tp))
    upper = base_tp + min(remaining, tied_tp)
    positives = int(y.sum())
    return {"n": len(y), "fraction": fraction, "k": k, "cutoff": cutoff,
            "tied_at_cutoff": tied_n, "remaining_at_cutoff": remaining,
            "expected_true_positives": expected, "true_positive_order_bounds": [lower, upper],
            "expected_precision": expected / k,
            "expected_recall": expected / positives if positives else None,
            "precision_order_bounds": [lower / k, upper / k],
            "interpretation": "Fractional expectation under exchangeable ties; bounds are ordering sensitivity, not confidence intervals."}


class WeightedMetrics:
    """Cache sorting and ties so block bootstrap does not repeatedly sort scores."""

    def __init__(self, y, probability):
        self.y = np.asarray(y, dtype=float)
        self.p = np.asarray(probability, dtype=float)
        self.order = np.argsort(-self.p, kind="stable")
        sorted_p = self.p[self.order]
        self.ends = np.r_[np.flatnonzero(np.diff(sorted_p)) , len(sorted_p) - 1]
        self.bin = np.minimum((self.p * 10).astype(int), 9)

    def compute(self, weights):
        weights = np.asarray(weights, dtype=float)
        positives = np.sum(weights * self.y)
        negatives = np.sum(weights * (1 - self.y))
        if positives <= 0 or negatives <= 0:
            return None
        w = weights[self.order]
        tp = np.cumsum(w * self.y[self.order])[self.ends]
        total = np.cumsum(w)[self.ends]
        fp = total - tp
        precision = np.divide(tp, total, out=np.zeros_like(tp), where=total > 0)
        ap = np.sum(np.diff(np.r_[0, tp]) * precision) / positives
        roc = np.trapz(np.r_[0, tp / positives], np.r_[0, fp / negatives])
        brier = np.sum(weights * (self.p - self.y) ** 2) / weights.sum()
        ece = np.abs(np.bincount(self.bin, weights * (self.y - self.p), minlength=10)).sum() / weights.sum()
        return np.asarray([ap, roc, brier, ece])


def date_block_weights(dates, repetitions=500, block_days=14, seed=42):
    if repetitions < 2 or block_days < 1:
        raise ValueError("Need >=2 repetitions and a positive block length")
    dates = pd.DatetimeIndex(dates)
    calendar = pd.date_range(dates.min(), dates.max(), freq="D")
    codes = calendar.get_indexer(dates)
    if len(calendar) < block_days:
        raise ValueError("Time interval shorter than requested bootstrap block")
    rng = np.random.default_rng(seed)
    count = int(np.ceil(len(calendar) / block_days))
    for _ in range(repetitions):
        starts = rng.integers(0, len(calendar) - block_days + 1, size=count)
        indices = (starts[:, None] + np.arange(block_days)).ravel()[:len(calendar)]
        yield np.bincount(indices, minlength=len(calendar))[codes]


def block_confidence_intervals(dates, y, probability, repetitions=500, block_days=14, seed=42):
    metric = WeightedMetrics(y, probability)
    samples = [metric.compute(w) for w in date_block_weights(dates, repetitions, block_days, seed)]
    samples = np.asarray([s for s in samples if s is not None])
    if len(samples) < 2:
        raise ValueError("Insufficient two-class bootstrap replicates")
    return {f"{name}_95CI": list(map(float, np.percentile(samples[:, i], [2.5, 97.5])))
            for i, name in enumerate(["PR-AUC", "ROC-AUC", "Brier", "ECE"])}


def paired_ap_difference(dates, y, a, b, repetitions=500, block_days=14, seed=42):
    ma, mb = WeightedMetrics(y, a), WeightedMetrics(y, b)
    differences = []
    for weights in date_block_weights(dates, repetitions, block_days, seed):
        first, second = ma.compute(weights), mb.compute(weights)
        if first is not None and second is not None:
            differences.append(float(first[0] - second[0]))
    if len(differences) < 2:
        raise ValueError("Insufficient paired bootstrap replicates")
    return {"observed_delta_AP": float(average_precision_score(y, a) - average_precision_score(y, b)),
            "delta_AP_95CI": list(map(float, np.percentile(differences, [2.5, 97.5]))),
            "replicates": len(differences), "block_days": block_days,
            "nonpositive_fraction_descriptive": float(np.mean(np.asarray(differences) <= 0)),
            "p_value": None, "interpretation": "Paired percentile CI; not a null-hypothesis p-value. Conditional on observed cells.",
            "differences": differences}

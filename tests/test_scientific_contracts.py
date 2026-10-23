"""Tests exercise production target, feature, quality and uncertainty functions."""

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from src.data.process_data import forward_target
from src.features.build_features import engineer_features, observed_dry_spell
from src.models.evaluation import WeightedMetrics, date_block_weights, paired_ap_difference


@pytest.mark.parametrize("horizon", [1, 3, 7])
@pytest.mark.parametrize("boundary", ["2023-01-01", "2024-01-01", "2024-03-01", "2025-01-01"])
def test_actual_target_embargo_future_injection(horizon, boundary):
    boundary = pd.Timestamp(boundary)
    dates = pd.date_range(boundary - pd.Timedelta(days=40), periods=80)
    counts = pd.Series(0, index=dates)
    labels_before = forward_target(counts, horizon)
    counts.loc[boundary:] = 10
    labels_after = forward_target(counts, horizon)
    cutoff = boundary - pd.Timedelta(days=horizon + 1)
    pd.testing.assert_series_equal(labels_before.loc[:cutoff], labels_after.loc[:cutoff])
    assert labels_after.iloc[-horizon:].isna().all()
    assert labels_after.loc[boundary - pd.Timedelta(days=1)] == 1
    assert labels_after.loc[boundary - pd.Timedelta(days=horizon + 1)] == 0


def test_actual_features_ignore_future_and_preserve_unknown_weather():
    dates = pd.date_range("2024-01-01", periods=60)
    frame = pd.DataFrame({"date": dates, "grid_id": "000_000", "grid_row": 0, "grid_col": 0,
                          "lat_center": -12., "lon_center": -55., "fire_count": 0,
                          "T2M_MAX": 30., "T2M_MIN": 20., "RH2M": 60., "WS10M": 3., "PRECTOTCORR": 2.})
    base = engineer_features(frame)
    frame.loc[40:, ["fire_count", "PRECTOTCORR"]] = 100
    changed = engineer_features(frame)
    pd.testing.assert_frame_equal(base.iloc[:40], changed.iloc[:40])
    frame.loc[20, "PRECTOTCORR"] = np.nan
    missing = engineer_features(frame)
    assert np.isnan(missing.loc[20, "dry_days"])
    assert missing.loc[20:26, "precip_sum_7d"].isna().all()


def test_unknown_spell_never_becomes_observed_dryness():
    result = observed_dry_spell(pd.Series([2, 0, np.nan, 0, 2, 0]))
    np.testing.assert_allclose(result, [0, 1, np.nan, np.nan, 0, 1], equal_nan=True)


def test_weighted_bootstrap_metrics_match_expanded_rows():
    y = np.array([0, 1, 0, 1, 1])
    p = np.array([.2, .8, .8, .6, .6])
    weights = np.array([2, 1, 0, 3, 1])
    expanded_y, expanded_p = np.repeat(y, weights), np.repeat(p, weights)
    result = WeightedMetrics(y, p).compute(weights)
    assert result[0] == pytest.approx(average_precision_score(expanded_y, expanded_p))
    assert result[1] == pytest.approx(roc_auc_score(expanded_y, expanded_p))
    assert result[2] == pytest.approx(brier_score_loss(expanded_y, expanded_p))


def test_paired_bootstrap_identical_models_has_zero_difference():
    dates = pd.date_range("2024-01-01", periods=40).repeat(2)
    y = np.tile([0, 1], 40)
    p = np.tile([.2, .8], 40)
    result = paired_ap_difference(dates, y, p, p, repetitions=10, block_days=7)
    assert result["delta_AP_95CI"] == [0., 0.]
    assert result["p_value"] is None
    for weights in date_block_weights(dates, repetitions=10, block_days=7):
        assert weights.sum() == len(dates)
        np.testing.assert_array_equal(weights[::2], weights[1::2])

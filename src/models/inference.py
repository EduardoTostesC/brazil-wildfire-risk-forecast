"""Shared feature and calibration contracts for training and serving."""

import numpy as np
import pandas as pd


def feature_matrix(df: pd.DataFrame, columns: list[str]) -> np.ndarray:
    """Preserve native NaN; reject absent columns and infinite/invalid values."""
    missing = sorted(set(columns) - set(df.columns))
    if not columns or missing:
        raise ValueError(f"Feature schema mismatch; missing columns: {missing}")
    values = df[columns].to_numpy(dtype=np.float32)
    if np.isinf(values).any():
        raise ValueError("Infinite feature values are invalid")
    return values


def calibrated_probabilities(model, calibrator, values: np.ndarray) -> np.ndarray:
    if model is None or calibrator is None:
        raise ValueError("Both model and fitted calibrator are required")
    raw = model.predict_proba(values)[:, 1]
    result = np.asarray(calibrator.calibrate(raw), dtype=float)
    if result.shape != (len(values),) or not np.isfinite(result).all() or ((result < 0) | (result > 1)).any():
        raise ValueError("Invalid calibrated probabilities")
    return result

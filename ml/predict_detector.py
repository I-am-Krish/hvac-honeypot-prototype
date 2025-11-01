# ml/predict_detector.py
import joblib
import numpy as np
import pandas as pd
from ml.feature_utils import add_features

MODEL_PATH = "models/attack_detector.pkl"
SCALER_PATH = "models/scaler.pkl"
FEAT_PATH = "models/feature_cols.pkl"

def load_model():
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    feature_cols = joblib.load(FEAT_PATH)
    return model, scaler, feature_cols

def make_features_for_event(event_dict, recent_df):
    """
    event_dict: {'ts': int unix, 'requested_power':float, 'applied_power':float, 'temperature':float, 'override': int}
    recent_df: pandas dataframe of recent events including the current one appended (same columns as logs/events.csv)
    Returns: 1D array of features aligned with feature_cols
    """
    # append event to recent_df and call add_features, then pull last row features
    df = recent_df.copy().reset_index(drop=True)
    # ensure event is last
    df = df.append(event_dict, ignore_index=True)
    df, feature_cols = add_features(df, window_seconds=10)
    last = df.iloc[-1]
    return last[feature_cols].values, feature_cols

def predict_event(event_dict, recent_df, threshold=0.7):
    model, scaler, feature_cols = load_model()
    X_vec, feat_cols = make_features_for_event(event_dict, recent_df)
    X_scaled = scaler.transform(X_vec.reshape(1,-1))
    prob = model.predict_proba(X_scaled)[0][1] if hasattr(model, "predict_proba") else model.predict(X_scaled)[0]
    is_attack = prob >= threshold
    return float(prob), bool(is_attack)

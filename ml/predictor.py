# ml/predictor.py
import joblib
import numpy as np
import pandas as pd

_model = None
_scaler = None
FEATURES = ['requested_power','applied_power','temperature','override']

def load(model_path='models/attack_detector_rf.pkl', scaler_path='models/scaler.pkl'):
    global _model, _scaler
    _model = joblib.load(model_path)
    _scaler = joblib.load(scaler_path)

def predict_event(event: dict):
    """
    event: dict with keys requested_power, applied_power, temperature, override (bool or 'True'/'False')
    returns: dict { label: 'attacker'|'tester', score: float (prob for attacker) }
    """
    if _model is None:
        load()
    x = [
        float(event.get('requested_power', 0)),
        float(event.get('applied_power', 0)),
        float(event.get('temperature', 0)),
        1 if str(event.get('override', False)) in ('True','true','1','1.0') else 0
    ]
    Xs = _scaler.transform([x])
    if hasattr(_model, "predict_proba"):
        score = _model.predict_proba(Xs)[0,1]
    else:
        # fallback to decision function or predict
        try:
            score = _model.decision_function(Xs)[0]
        except:
            score = float(_model.predict(Xs)[0])
    label = 'attacker' if score >= 0.5 else 'tester'
    return {'label': label, 'score': float(score)}
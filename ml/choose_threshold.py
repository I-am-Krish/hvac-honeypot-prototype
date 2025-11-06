# ml/choose_threshold.py
import joblib,pandas as pd
from sklearn.metrics import precision_recall_curve
import numpy as np
df = pd.read_csv('dataset/events_features.csv')
X = df[['requested_power','applied_power','temperature','override',
        'delta_requested','delta_applied','delta_temp','inter_arrival_s',
        'rolling_req_3','rolling_app_3','count_last_30s']].fillna(0)
y = df['label']
clf = joblib.load('models/attack_detector_xgb_features.pkl')
scaler = joblib.load('models/scaler_xgb_features.pkl')
proba = clf.predict_proba(scaler.transform(X))[:,1]
prec, rec, th = precision_recall_curve(y, proba)
# show candidate thresholds (sorted by F1)
f1 = 2 * (prec * rec) / (prec + rec + 1e-9)
best = np.argmax(f1)
print("Best threshold by F1:", th[best] if best < len(th) else 1.0)
# list top thresholds
order = np.argsort(-f1)[:10]
for idx in order:
    t = th[idx] if idx < len(th) else 1.0
    print(f"thr={t:.3f} prec={prec[idx]:.3f} rec={rec[idx]:.3f} f1={f1[idx]:.3f}")
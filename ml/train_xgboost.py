# ml/train_xgboost.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from xgboost import XGBClassifier
import joblib
from collections import Counter

# === Load dataset ===
df = pd.read_csv('dataset/events_combined.csv')
print(f"[INFO] Loaded {len(df)} rows")
print(df['role'].value_counts())

# === Feature engineering ===
df['override'] = df['override'].astype(str).map({'True':1, 'False':0})
X = df[['requested_power', 'applied_power', 'temperature', 'override']].fillna(0)
y = df['role'].map({'attacker':1, 'tester':0})

# === Train/test split ===
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
print(f"[INFO] Train: {len(y_train)}, Test: {len(y_test)}")
print("[INFO] Class distribution:", Counter(y_train))

# === Scale features ===
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# === Handle imbalance ===
ratio = Counter(y_train)
scale_pos_weight = ratio[0] / ratio[1] if 1 in ratio and 0 in ratio else 1.0
print(f"[INFO] scale_pos_weight set to {scale_pos_weight:.2f}")

# === Train XGBoost ===
xgb = XGBClassifier(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    eval_metric='logloss',
    use_label_encoder=False
)

xgb.fit(X_train_scaled, y_train)
y_pred = xgb.predict(X_test_scaled)
y_proba = xgb.predict_proba(X_test_scaled)[:, 1]

# === Evaluation ===
print("\n=== Classification Report ===")
print(classification_report(y_test, y_pred, target_names=['tester', 'attacker']))
print("=== Confusion Matrix ===")
print(confusion_matrix(y_test, y_pred))
print("ROC-AUC:", roc_auc_score(y_test, y_proba))

# === Save model + scaler ===
import os
os.makedirs('models', exist_ok=True)
joblib.dump(xgb, 'models/attack_detector_xgb.pkl')
joblib.dump(scaler, 'models/scaler_xgb.pkl')
print("\n[INFO] Saved model → models/attack_detector_xgb.pkl")
print("[INFO] Saved scaler → models/scaler_xgb.pkl")
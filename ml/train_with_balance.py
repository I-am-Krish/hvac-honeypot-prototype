# ml/train_with_balance.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from collections import Counter
import joblib

# === Load dataset ===
df = pd.read_csv('dataset/events_combined.csv')  # or 'logs/events.csv'
print(f"[INFO] Loaded dataset with {len(df)} rows")
print(df['role'].value_counts())

# === Feature preparation ===
df['override'] = df['override'].astype(str).map({'True': 1, 'False': 0})
X = df[['requested_power', 'applied_power', 'temperature', 'override']].fillna(0)
y = df['role'].map({'attacker': 1, 'tester': 0})

# === Scale features ===
scaler = StandardScaler()
Xs = scaler.fit_transform(X)

# === Train-test split ===
Xtr, Xte, ytr, yte = train_test_split(
    Xs, y, test_size=0.2, stratify=y, random_state=42
)
print(f"[INFO] Training samples: {len(ytr)}, Testing samples: {len(yte)}")
print("[INFO] Class distribution in training set:", Counter(ytr))

# === Handle imbalance safely ===
minority_class_size = Counter(ytr)[0] if 0 in Counter(ytr) else 0
if minority_class_size < 6:
    print(f"[INFO] Too few minority samples ({minority_class_size}) — skipping SMOTE.")
    Xtr_sm, ytr_sm = Xtr, ytr
else:
    print(f"[INFO] Applying SMOTE (minority class size: {minority_class_size}) ...")
    sm = SMOTE(random_state=42)
    Xtr_sm, ytr_sm = sm.fit_resample(Xtr, ytr)
print("[INFO] New training class distribution:", Counter(ytr_sm))

# === Train classifier ===
clf = RandomForestClassifier(
    n_estimators=200, class_weight='balanced', random_state=42
)
clf.fit(Xtr_sm, ytr_sm)

# === Evaluate model ===
yhat = clf.predict(Xte)
print("\n=== Classification Report ===")
print(classification_report(yte, yhat, target_names=['tester', 'attacker']))
print("=== Confusion Matrix ===")
print(confusion_matrix(yte, yhat))

# === Save artifacts ===
import os
os.makedirs("models", exist_ok=True)
joblib.dump(clf, 'models/attack_detector_rf.pkl')
joblib.dump(scaler, 'models/scaler.pkl')
print("\n[INFO] Saved model → models/attack_detector_rf.pkl")
print("[INFO] Saved scaler → models/scaler.pkl")
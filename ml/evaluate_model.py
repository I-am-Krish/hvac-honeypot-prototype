# ml/evaluate_model.py
import pandas as pd
import joblib
import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
from collections import Counter

# load dataset
df = pd.read_csv('dataset/events_combined.csv')
df['override'] = df['override'].astype(str).map({'True':1,'False':0})
X = df[['requested_power','applied_power','temperature','override']].fillna(0)
y = df['role'].map({'attacker':1,'tester':0})

# load artifacts
clf = joblib.load('models/attack_detector_rf.pkl')
scaler = joblib.load('models/scaler.pkl')

# full CV
Xs = scaler.transform(X)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(clf, Xs, y, cv=cv, scoring='roc_auc')
print("5-fold ROC AUC scores:", scores, "mean:", np.mean(scores))

# holdout evaluation
Xtr, Xte, ytr, yte = train_test_split(Xs, y, test_size=0.2, stratify=y, random_state=42)
yhat = clf.predict(Xte)
yproba = clf.predict_proba(Xte)[:,1] if hasattr(clf, "predict_proba") else None
print("\nClassification report (holdout):")
print(classification_report(yte, yhat, target_names=['tester','attacker']))
print("Confusion matrix:\n", confusion_matrix(yte, yhat))
if yproba is not None:
    print("Holdout ROC AUC:", roc_auc_score(yte, yproba))

# quick class balance
print("\nClass distribution:", Counter(y))
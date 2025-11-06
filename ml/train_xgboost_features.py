# ml/train_xgboost_features.py
import pandas as pd, os
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
from collections import Counter
from imblearn.over_sampling import SMOTE
import numpy as np

fn = 'dataset/events_features.csv'
if not os.path.exists(fn):
    raise SystemExit(f"{fn} missing - run feature_engineer.py first")

df = pd.read_csv(fn)
X = df[['requested_power','applied_power','temperature','override',
        'delta_requested','delta_applied','delta_temp','inter_arrival_s',
        'rolling_req_3','rolling_app_3','count_last_30s']].fillna(0)
y = df['label']

# holdout: choose one archive folder as final holdout (we assume you created archives; here we do a simple train/test split)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
print("Train/Test:", len(y_train), len(y_test))
print("Train class dist:", Counter(y_train))

# scale
scaler = StandardScaler()
Xtr_s = scaler.fit_transform(X_train)
Xte_s = scaler.transform(X_test)

# SMOTE on TRAIN fold only if minority >= 6
from collections import Counter
min_class = Counter(y_train)[0] if 0 in Counter(y_train) else 0
if min_class >= 6:
    sm = SMOTE(random_state=42)
    Xtr_s, ytr_s = sm.fit_resample(Xtr_s, y_train)
    print("[INFO] Applied SMOTE:", Counter(ytr_s))
else:
    Xtr_s, ytr_s = Xtr_s, y_train
    print("[INFO] Skipped SMOTE, minority size:", min_class)

# xgboost with scale_pos_weight (still useful)
neg = sum(ytr_s==0)
pos = sum(ytr_s==1)
scale_pos_weight = neg/pos if pos>0 else 1.0
print("scale_pos_weight:", scale_pos_weight)

clf = XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=4,
                    subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
                    scale_pos_weight=scale_pos_weight, use_label_encoder=False,
                    eval_metric='logloss', random_state=42)
clf.fit(Xtr_s, ytr_s)

# eval
yhat = clf.predict(Xte_s)
yprob = clf.predict_proba(Xte_s)[:,1]
print("\nClassification report:")
print(classification_report(y_test, yhat, target_names=['tester','attacker']))
print("Conf matrix:\n", confusion_matrix(y_test,yhat))
print("ROC-AUC:", roc_auc_score(y_test, yprob))

# save
os.makedirs('models', exist_ok=True)
joblib.dump(clf, 'models/attack_detector_xgb_features.pkl')
joblib.dump(scaler, 'models/scaler_xgb_features.pkl')
print("Saved model & scaler")
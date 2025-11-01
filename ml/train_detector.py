# ml/train_detector.py
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from ml.feature_utils import prepare_events_df, add_features

def main(csv_path="logs/events.csv", out_dir="models"):
    os.makedirs(out_dir, exist_ok=True)
    df = prepare_events_df(csv_path)
    df, feature_cols = add_features(df, window_seconds=10)

    # label: if role column exists we use it. else fallback to override==1 as weak label.
    if 'role' in df.columns:
        df['label'] = (df['role'].astype(str) == 'attacker').astype(int)
    else:
        df['label'] = (df['override'] == 1).astype(int)

    X = df[feature_cols]
    y = df['label']

    # handle tiny datasets: if class imbalance, use stratify
    test_size = 0.25 if len(df) > 20 else 0.4
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42, stratify=y if y.nunique()>1 else None)

    # scale features
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # basic XGBoost with small grid search (fast)
    model = XGBClassifier(use_label_encoder=False, eval_metric='logloss', n_jobs=4)
    param_grid = {
        'n_estimators': [50, 100],
        'max_depth': [3, 5],
        'learning_rate': [0.1, 0.01]
    }
    clf = GridSearchCV(model, param_grid, cv=3, scoring='f1' if y_train.sum()>0 else 'accuracy', n_jobs=4, verbose=0)
    clf.fit(X_train_s, y_train)

    best = clf.best_estimator_
    print("Best params:", clf.best_params_)

    preds = best.predict(X_test_s)
    probs = best.predict_proba(X_test_s)[:,1] if hasattr(best, "predict_proba") else None

    print("Classification report:")
    print(classification_report(y_test, preds, zero_division=0))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, preds))

    # save model and scaler and feature list
    joblib.dump(best, os.path.join(out_dir, "attack_detector.pkl"))
    joblib.dump(scaler, os.path.join(out_dir, "scaler.pkl"))
    # save features for runtime
    joblib.dump(feature_cols, os.path.join(out_dir, "feature_cols.pkl"))
    print("Saved model and artifacts to", out_dir)

if __name__ == "__main__":
    main()
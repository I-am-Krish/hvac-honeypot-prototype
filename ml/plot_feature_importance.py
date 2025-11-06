# ml/plot_feature_importance.py
import joblib, pandas as pd, matplotlib.pyplot as plt, os
clf = joblib.load('models/attack_detector_rf.pkl')
features = ['requested_power','applied_power','temperature','override']
importances = clf.feature_importances_
df = pd.DataFrame({'feature':features, 'importance':importances}).sort_values('importance', ascending=False)
print(df)
os.makedirs('models', exist_ok=True)
df.to_csv('models/feature_importances.csv', index=False)
plt.barh(df['feature'], df['importance'])
plt.title('Feature importances (RandomForest)')
plt.xlabel('Importance')
plt.tight_layout()
plt.savefig('models/feature_importance.png')
print("Saved models/feature_importances.csv and models/feature_importance.png")
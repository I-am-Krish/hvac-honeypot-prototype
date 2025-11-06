import shap
import matplotlib.pyplot as plt
import joblib
import pandas as pd
import os

# Load model + data (as before)
model = joblib.load('models/attack_detector_xgb_features.pkl')
scaler = joblib.load('models/scaler_xgb_features.pkl')
df = pd.read_csv('dataset/events_features.csv')

feature_cols = [
    'requested_power','applied_power','temperature','override',
    'delta_requested','delta_applied','delta_temp','inter_arrival_s',
    'rolling_req_3','rolling_app_3','count_last_30s'
]
X = df[feature_cols]
explainer = shap.Explainer(model)
shap_values = explainer(X)

# Pick a sample
i = 5
sample = X.iloc[i, :]

# --- Create and adjust force plot ---
shap.force_plot(
    explainer.expected_value,
    shap_values.values[i, :],
    sample,
    matplotlib=True,
    show=False
)

# --- Matplotlib adjustments ---
plt.gcf().set_size_inches(12, 3)    # Wider aspect ratio
plt.tight_layout(pad=3.5)           # Add extra padding around plot
plt.subplots_adjust(top=0.88)       # Move “higher/lower” and base label upward
plt.rcParams.update({'font.size': 12})  # Increase label font size

# Save high-quality output
os.makedirs('results', exist_ok=True)
plt.savefig('results/shap_force_adjusted.png', dpi=300, bbox_inches='tight')
plt.show()
import yaml

class SafetyFilter:
    def __init__(self, config):
        # config: dict with T_min, T_max, dt, smoothing_alpha
        self.T_min = float(config.get('T_min', 18.0))
        self.T_max = float(config.get('T_max', 26.0))
        self.alpha = float(config.get('smoothing_alpha', 1.0))

    def filter(self, T_current, P_requested, simulate_step_fn):
        """
        simulate_step_fn(applied_power) -> predicted_temp
        Returns (applied_power, override_flag)
        Simple approach: try requested power; if predicted temp outside bounds, reduce power.
        """
        applied = float(P_requested)
        predicted = simulate_step_fn(applied)
        override = False
        if predicted < self.T_min:
            # requested power was too low (room too cold next step) -> increase power but smoothly
            override = True
            applied = min(1.0, applied + self.alpha * (self.T_min - predicted)/10.0)
        elif predicted > self.T_max:
            # requested power leads to overheating -> reduce
            override = True
            applied = max(0.0, applied - self.alpha * (predicted - self.T_max)/10.0)
        return applied, override

def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

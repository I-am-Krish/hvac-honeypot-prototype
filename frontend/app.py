from flask import Flask, request, jsonify
import csv, os, time
import sys
sys.path.append("../simulator")
sys.path.append("../scc")

from simulator.room import RoomSimulator
from scc.safety_filter import SafetyFilter, load_config

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(DATA_DIR, exist_ok=True)
LOGFILE = os.path.join(DATA_DIR, "events.csv")

# global simple instances (for prototype/demo)
sim = RoomSimulator()
config = load_config(os.path.join(os.path.dirname(__file__), "..", "scc", "config.yaml"))
sfilter = SafetyFilter(config)

def log_event(rec):
    header = ["ts", "role", "requested_power", "applied_power", "temperature", "override"]
    write_header = not os.path.exists(LOGFILE)
    with open(LOGFILE, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(header)
        writer.writerow(rec)

@app.route("/sensor/temperature", methods=["GET"])
def get_temp():
    return jsonify({"temperature": sim.T})

@app.route("/actuator/heater", methods=["POST"])
def set_heater():
    data = request.json or {}
    power = float(data.get("power", 0.0))
    role = data.get("role", "user")
    # define simulate_step_fn that uses the simulator's current state (preview)
    def simulate_step_fn(p):
        # create a temporary copy of sim state for prediction
        temp = sim.T
        # use same dynamics calculation as step but don't mutate sim
        dT_dt = (1.0/sim.C) * (-(temp - sim.T_out)/sim.R + sim.eta * float(p))
        pred = temp + dT_dt * (sim.dt / 60.0)
        return pred
    applied, override = sfilter.filter(sim.T, power, simulate_step_fn)
    # apply to simulator
    newT = sim.step(P_heater=applied)
    ts = int(time.time())
    log_event([ts, role, power, applied, newT, override])
    return jsonify({"requested_power": power, "applied_power": applied, "temperature": newT, "override": override})

if __name__ == "__main__":
    app.run(port=5000, host="127.0.0.1")

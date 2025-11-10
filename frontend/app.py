from flask import Flask, request, jsonify, send_from_directory
import csv, os, time, threading
import sys
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
# ensure simulator and scc packages are importable regardless of cwd
# add repository root so `import simulator.room` and `import scc.safety_filter` work
sys.path.insert(0, ROOT)

from simulator.room import RoomSimulator
from scc.safety_filter import SafetyFilter, load_config

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(DATA_DIR, exist_ok=True)
LOGFILE = os.path.join(DATA_DIR, "events.csv")

# Engagement tracking state
_last_seen = {}  # client_ip -> last_ts
_active = set()  # client_ip currently in an active session
ENGAGEMENT_GAP = int(os.environ.get('ENGAGEMENT_GAP', '120'))  # seconds


def _engagement_monitor():
    """Background thread: closes sessions when inactivity > ENGAGEMENT_GAP"""
    while True:
        now = int(time.time())
        to_close = []
        for client in list(_active):
            last = _last_seen.get(client, 0)
            if now - last > ENGAGEMENT_GAP:
                to_close.append(client)
        for c in to_close:
            # write an engagement_end marker
            ts = int(time.time())
            try:
                    # fill new columns: request_path, request_method, client_id
                    log_event([ts, 'system', None, None, None, None, c, '', '', '', f'{c}', 'engagement_end'])
            except Exception:
                pass
            _active.discard(c)
        time.sleep(max(5, ENGAGEMENT_GAP // 4))


# start background thread
_monitor_thread = threading.Thread(target=_engagement_monitor, daemon=True)
_monitor_thread.start()

# global simple instances (for prototype/demo)
sim = RoomSimulator()
config = load_config(os.path.join(os.path.dirname(__file__), "..", "scc", "config.yaml"))
sfilter = SafetyFilter(config)

def log_event(rec):
    # Support optional event_type column as last element in rec
    header = ["ts", "role", "requested_power", "applied_power", "temperature", "override", "client_ip", "user_agent", "request_path", "request_method", "client_id", "event_type"]
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
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "invalid json"}), 400
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
    # capture client identity info to allow session/engagement analysis
    # prefer X-Forwarded-For when present (useful behind proxies)
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        # take first ip in list
        client_ip = xff.split(',')[0].strip()
    else:
        client_ip = request.remote_addr
    user_agent = request.headers.get("User-Agent", "")
    request_path = request.path
    request_method = request.method
    client_id = f"{client_ip}|{user_agent}"

    # engagement start detection: if unseen or gap exceeded, emit a start marker
    last = _last_seen.get(client_ip)
    if last is None or (ts - last) > ENGAGEMENT_GAP:
        try:
            log_event([ts, 'system', None, None, None, None, client_ip, user_agent, request_path, request_method, client_id, 'engagement_start'])
        except Exception:
            pass
        _active.add(client_ip)

    # update last seen
    _last_seen[client_ip] = ts

    # log the actual event
    log_event([ts, role, power, applied, newT, override, client_ip, user_agent, request_path, request_method, client_id, 'event'])
    return jsonify({"requested_power": power, "applied_power": applied, "temperature": newT, "override": override})

if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")


@app.route('/api/sessions', methods=['GET'])
def api_sessions():
    """Return sessions CSV as JSON list for the dashboard."""
    sessions_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'engagement_sessions.csv')
    if not os.path.exists(sessions_path):
        return jsonify({'error': 'sessions not generated yet'}), 404
    import pandas as pd
    df = pd.read_csv(sessions_path)
    return jsonify(df.to_dict(orient='records'))


@app.route('/dashboard', methods=['GET'])
def dashboard_page():
    """Simple dashboard page that shows generated plots and refreshes every 10s."""
    plots_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'plots')
    plots = []
    if os.path.exists(plots_dir):
        for fname in sorted(os.listdir(plots_dir)):
            if fname.lower().endswith('.png'):
                plots.append('/static/plots/' + fname)
    # create a tiny HTML that shows images
    html_parts = ["<html><head><meta http-equiv='refresh' content='10'><title>Honeypot Dashboard</title></head><body>"]
    html_parts.append('<h2>Engagement Sessions</h2>')
    if not plots:
        html_parts.append('<p>No plots yet. Run the engagement analyzer to generate plots.</p>')
    else:
        for p in plots:
            html_parts.append(f"<div><img src='{p}' style='max-width:900px;width:90%;'><p>{p}</p></div>")
    html_parts.append('</body></html>')
    return '\n'.join(html_parts)


@app.route('/static/plots/<path:filename>')
def serve_plot(filename):
    plots_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'plots'))
    return send_from_directory(plots_dir, filename)
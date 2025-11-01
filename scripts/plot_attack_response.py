import pandas as pd
import matplotlib.pyplot as plt

# Load your log file
df = pd.read_csv("logs/events.csv")

# Time or index axis
x = range(len(df))

# --- Plot 1: Requested vs Applied Power ---
plt.figure(figsize=(10,4))
plt.step(x, df["requested_power"], where="post", label="Requested Power (Attacker)", color="red", alpha=0.7)
plt.step(x, df["applied_power"], where="post", label="Applied Power (After SCC)", color="blue", alpha=0.7)
plt.title("Attacker Requests vs SCC Response")
plt.xlabel("Event Index")
plt.ylabel("Power Level")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()
plt.savefig("attack_response_plot1.png")

# --- Plot 2: Temperature Stability ---
plt.figure(figsize=(10,4))
plt.plot(x, df["temperature"], label="Room Temperature", lw=2)
plt.axhline(18, color="red", linestyle="--", alpha=0.5, label="Min safe bound")
plt.axhline(26, color="red", linestyle="--", alpha=0.5, label="Max safe bound")
plt.scatter([i for i,v in enumerate(df["override"]) if v], 
            df["temperature"][df["override"]==True], 
            color="orange", s=40, label="SCC override points")
plt.title("Temperature Stability During Attack")
plt.xlabel("Event Index")
plt.ylabel("Temperature (°C)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()
plt.savefig("attack_response_plot2.png")
from room import RoomSimulator

def main():
    sim = RoomSimulator()
    temps = []
    P = 0.0
    for step in range(60):
        # simple scheduled heater: on for first 30 steps
        P = 1.0 if step < 30 else 0.0
        T = sim.step(P_heater=P)
        temps.append(T)
        print(f"step={step:02d} P={P:.1f} T={T:.2f}")
if __name__ == "__main__":
    main()

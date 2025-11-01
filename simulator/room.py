class RoomSimulator:
    def __init__(self, T0=22.0, T_out=10.0, R=1.0, C=1.0, eta=0.9, dt=60):
        self.T = float(T0)
        self.T_out = float(T_out)
        self.R = float(R)
        self.C = float(C)
        self.eta = float(eta)
        self.dt = float(dt)

    def step(self, P_heater=0.0, disturbance=0.0):
        # Simple first-order thermal model.
        # dT/dt = (1/C) * ( -(T - T_out)/R + eta*P + disturbance )
        dT_dt = (1.0/self.C) * (-(self.T - self.T_out)/self.R + self.eta * float(P_heater) + float(disturbance))
        # integrate using Euler method: T_new = T + dT_dt * (dt seconds)
        # dt is in seconds; we scale by 1.0 for seconds
        self.T += dT_dt * (self.dt / 60.0)  # scale to minutes if desired
        return self.T

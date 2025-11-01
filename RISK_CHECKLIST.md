# Risk checklist & containment (short)

- Do not expose frontend ports to the public Internet.
- Use an isolated VM / internal Docker network.
- Block outbound connections from the honeypot VM (honeywall recommended).
- Label repo: "research prototype — not for production".
- Maintain logs locally; do not forward logs to external services without review.

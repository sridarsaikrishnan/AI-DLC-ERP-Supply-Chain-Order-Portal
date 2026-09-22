# Tech Stack Decisions — U1 Identity & Access

Inherits the whole U0 stack. U1-specific additions:

| Concern | Decision | Rationale |
|---|---|---|
| Token | Stateless signed token via PyJWT | In-process verification (NFR-U1-PERF-1); no session store |
| MFA | TOTP via pyotp | Standard authenticator-app flow, no external provider (Q2=A) |
| Password storage | As-is (Q7=A) | Explicit PoC decision; hashing flagged for hardening |

These add `PyJWT` and `pyotp` to `requirements.txt` during code generation.

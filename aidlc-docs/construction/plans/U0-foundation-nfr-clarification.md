# NFR Clarification — U0 Foundation (Q7 confirmation)

Your answers are consistent; this is one confirmation on a consequential item.

## Clarification: Q7 = B (no minimal security safeguards)
You chose B — skip even the minimal safeguards. I want to make sure of the scope, because two of those "safeguards" are things that are painful to retrofit and one is a near-universal default:

- **Password storage**: U1 Identity handles login. If we don't hash passwords, we'd be storing them in plaintext, which is a data-breach liability even in a PoC and awkward to reverse later.
- **ERP credentials in the domain model**: the U0 design already keeps credentials as a `connectionRef` (not stored in the domain entity). Q7=B would revert that and place real ERP credentials directly in the config records.
- **Parameterized queries**: this is the default way to query in essentially every Python DB library; NOT doing it means deliberately building string-concatenated SQL, which is more work and creates injection risk.

Given that, how do you want to proceed?

A) Keep Q7=B literally: plaintext passwords, credentials inline in domain model, no parameterized-query guidance. (Maximum "PoC simplicity", accepts the risks above.)

B) Actually keep the three minimal hygiene items (hash passwords, credentials by reference, parameterized queries) — they're low effort and avoid painful retrofits, while still NOT enabling the full security baseline. (recommended)

C) Keep only password hashing + parameterized queries (both effectively free), but allow credentials inline in the config for now.

D) Other (please describe after [Answer]: tag below)

[Answer]: A

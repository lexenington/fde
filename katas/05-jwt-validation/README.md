# Kata 5: validate an access token

**Time-box: 60 minutes.** Used in: 02/02 (OIDC SSO), Savanna (officer tokens), the *claims-change* card.

**The task.** Implement `validate` in `jwt_validation.py` with `pyjwt`. `python -m pytest -q katas/05-jwt-validation`. (The tests generate their own RSA keys; nothing needs to be running.)

**What a security lead looks for**
- the key comes from the JWKS, by `kid`, and the **algorithm is pinned by you**, not read from the token. That is what stops `alg: none` and the HS256-with-the-public-key trick
- `aud` and `iss` are required *and* checked. A valid signature from the right IdP for a *different app* is not a login
- `exp` must exist
- every rejection is the same exception, so a caller can't leak why
- `pyjwt` checks `exp` against the real clock, but the tests pin the time with `now`. Controlling the clock in tests is the same habit as kata 1 and 2: make time a parameter

**Then.** Real JWKS endpoints rotate keys. Where would you cache the key set, for how long, and what do you do when you see a `kid` you don't know?

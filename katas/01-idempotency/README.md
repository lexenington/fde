# Kata 1: idempotency store

**Time-box: 45 minutes.** Used in: 02/02 (idempotent CRM sync, webhook de-duplication), Lakeside's double "yes".

**The task.** `idempotency.py` has an `IdempotencyStore` with no body. Make `python -m pytest -q katas/01-idempotency` go green.

**What the tests are really asking**
- same key twice means the function runs once and both calls get the same result, including a result that is falsy
- a failure is not remembered, so the client's retry can succeed
- entries expire (the clock is injected so tests don't sleep)
- eight threads with the same key run the function **once**, and the other seven wait for the answer
- two *different* keys never wait for each other

**Think of a Mobile Money payment.** A customer taps *Pay* on a slow connection, sees nothing, and taps again. Without an idempotency key the second tap is a second charge, and the support call lands on *you*. The key is the customer's intent (this order, this payment), not the HTTP request.

**Rules.** Standard library only. No `time.sleep` in your code.

**Then.** Where would this live in your 02/02 app, and what would the key be for a webhook? For a booking? What happens to your guarantee if the process restarts, and what would you change to survive that?

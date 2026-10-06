# Kata 4: verify a webhook signature

**Time-box: 40 minutes.** Used in: 02/02 (signed CRM webhooks), the *secret-rotation* card, Lakeside's WhatsApp webhook.

**The task.** Implement `verify` in `webhook_signature.py`. `python -m pytest -q katas/04-webhook-signature`.

**Gotchas the tests encode**
- sign the **raw bytes** you received, never a re-serialised JSON body
- the timestamp is inside the signature, so an attacker can't just refresh it
- more than one `v1=` means a rotation is in progress: any match counts
- bad input returns `False`, it doesn't throw (a 500 on a forged request tells the attacker something)
- compare with `hmac.compare_digest`, not `==`

**Then.** Write down what your endpoint should return for: a bad signature, a stale timestamp, and a good signature on an event you've already processed (kata 1).

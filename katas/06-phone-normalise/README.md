# Kata 6: normalise Ghana phone numbers

**Time-box: 30 minutes.** Used in: 02/01 (entity resolution), Lakeside (a returning patient stored as `024…` messaging from `+23324…`), Savanna (member lookup by phone).

**The task.** Implement `normalise_gh_phone` and `same_phone` in `phone_normalise.py`. `python -m pytest -q katas/06-phone-normalise`. No `phonenumbers` library: the point is to see the rules.

**Notes**
- decide the order: strip punctuation, then handle the country code, then the leading 0, then validate
- "invalid" must be `None`, never a guess. A wrong number merged into a real person is worse than a missing one
- `same_phone` of two junk values is `False`: two "N/A"s are not the same customer

**Then.** In the Lakeside database the stored number is whatever a form saved in 2019, and `create_booking` matches on the exact string. How do you pass it the *stored* spelling of an existing patient's number?

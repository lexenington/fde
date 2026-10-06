"""Kata 9: chunk a policy manual for retrieval.

A chunk that starts mid-sentence, or loses the section number it belongs to, is a chunk your copilot can't cite.
"""


def chunk_manual(text: str, max_chars: int = 600) -> list[dict]:
    """Split a manual into retrieval chunks. The manual looks like this:

        Part 4. Individual loans
        4.2 Amounts
        4.2.1 Maximum amount, first loan
        The maximum amount for a first individual loan is GHS 5,000. It may be reduced by circular.
        4.2.2 Maximum amount, repeat borrowers
        ...

    Lines that start `Part N.` are part headings, lines like `4.2 Title` are sub-section headings, and lines like
    `4.2.1 Title` start a rule; the rule's body is every line after it until the next heading.

    Return one dict per chunk with these keys:
      id       "4.2.1" for the whole rule, or "4.2.1#1", "4.2.1#2"... when a long rule had to be split
      section  "4.2.1"
      title    "Maximum amount, first loan"
      path     the headings above it, outermost first, e.g. ["Part 4. Individual loans", "4.2 Amounts"]
      text     starts with "4.2.1 Maximum amount, first loan" on its own line, then the body, so a chunk is
               self-describing even when retrieved alone

    Rules: a chunk never crosses a rule boundary. A rule whose text would exceed `max_chars` is split between
    sentences (never inside one), into as few chunks as possible with greedy packing; each piece repeats the
    heading line. A single sentence longer than `max_chars` stays whole. No body text is lost or duplicated.
    """
    raise NotImplementedError

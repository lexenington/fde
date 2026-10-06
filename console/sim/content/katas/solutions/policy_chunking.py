import re

_PART = re.compile(r"^Part \d+\.")
_SUB = re.compile(r"^\d+\.\d+\s+\S")
_RULE = re.compile(r"^(\d+\.\d+\.\d+)\s+(\S.*)$")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def chunk_manual(text, max_chars=600):
    chunks, part, sub, cur = [], None, None, None

    def flush():
        if not cur:
            return
        heading = f"{cur['section']} {cur['title']}"
        body = " ".join(l.strip() for l in cur["lines"] if l.strip())
        pieces, now = [], []
        for s in (_SENT.split(body) if body else []):
            if now and len(heading) + 1 + len(" ".join(now + [s])) > max_chars:
                pieces.append(now)
                now = []
            now.append(s)
        if now or not pieces:
            pieces.append(now)
        for i, piece in enumerate(pieces, 1):
            chunks.append({"id": cur["section"] if len(pieces) == 1 else f"{cur['section']}#{i}", "section": cur["section"],
                           "title": cur["title"], "path": [p for p in (cur["part"], cur["sub"]) if p],
                           "text": heading + "\n" + " ".join(piece)})

    for line in text.splitlines():
        s = line.strip()
        m = _RULE.match(s)
        if _PART.match(s):
            flush(); cur, part, sub = None, s, None
        elif m:
            flush()
            cur = {"section": m.group(1), "title": m.group(2), "part": part, "sub": sub, "lines": []}
        elif _SUB.match(s):
            flush(); cur, sub = None, s
        elif cur is not None:
            cur["lines"].append(line)
    flush()
    return chunks

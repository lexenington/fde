# Kata 9: chunk a policy manual for retrieval

**Time-box: 60 minutes.** Used in: Savanna (the 139-page credit policy), any RAG over documents with numbered sections.

**The task.** Implement `chunk_manual` in `policy_chunking.py`. `python -m pytest -q katas/09-policy-chunking`.

**Why it matters.** Esi's rule is *every answer cites the section*. A chunk that has lost its section number can't be cited, and a chunk split mid-sentence can contradict itself ("...is GHS 5," / "000 unless a circular..."). Chunking by *structure* first, and by size only when you must, is most of the retrieval quality.

**Think about**
- headings first: a line's shape decides whether it is a part, a sub-section, a rule or body text
- the heading line goes into every piece, so each chunk stands alone when retrieved
- sentence splitting: `GHS 5,000.` and `4.0%` contain a `.` or `,` that is not the end of a sentence

**Then.** Run it on the real manual (`console/.savanna-data/share/Credit-Policy-Manual-v7.pdf`, after extracting the text with `pypdf`). Which parts of that PDF break your assumptions about headings?

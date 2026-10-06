def cluster(pairs, ids):
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for i in ids:
        find(i)
    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    groups = {}
    for x in list(parent):
        groups.setdefault(find(x), set()).add(x)
    return list(groups.values())


def _pairs(clusters):
    out = set()
    for c in clusters:
        items = sorted(c)
        out |= {(items[i], items[j]) for i in range(len(items)) for j in range(i + 1, len(items))}
    return out


def pairwise_f1(predicted, truth):
    p, t = _pairs(predicted), _pairs(truth)
    hit = len(p & t)
    precision = hit / len(p) if p else 1.0
    recall = hit / len(t) if t else 1.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1

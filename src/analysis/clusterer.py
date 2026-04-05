"""
Similarity clustering — group images whose pHash Hamming distance is within
a configurable threshold using a union-find (disjoint set union) structure.

Pure Python, no Qt dependency.
"""

from __future__ import annotations

from pathlib import Path

import imagehash


# ---------------------------------------------------------------------------
# Union-find
# ---------------------------------------------------------------------------

class _UnionFind:
    def __init__(self, keys: list) -> None:
        self._parent: dict = {k: k for k in keys}
        self._rank: dict = {k: 0 for k in keys}

    def find(self, x):
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]  # path compression
            x = self._parent[x]
        return x

    def union(self, a, b) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cluster(
    hashes: dict[Path, imagehash.ImageHash],
    threshold: int = 10,
) -> tuple[list[list[Path]], list[Path]]:
    """
    Group image paths into similarity clusters.

    Two images are placed in the same group when their pHash Hamming
    distance is ≤ threshold.

    Parameters
    ----------
    hashes     : mapping of Path → pHash for each image
    threshold  : max Hamming distance to consider images similar (0–64)

    Returns
    -------
    (groups, unique)
        groups  — list of groups, each group is a list of ≥ 2 Paths,
                  sorted by group size descending
        unique  — list of Paths that are not similar to any other image
    """
    paths = list(hashes.keys())
    if not paths:
        return [], []

    uf = _UnionFind(paths)

    # O(n²) pairwise comparison — acceptable for n ≤ 500
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            dist = hashes[paths[i]] - hashes[paths[j]]
            if dist <= threshold:
                uf.union(paths[i], paths[j])

    # Collect groups
    buckets: dict = {}
    for path in paths:
        root = uf.find(path)
        buckets.setdefault(root, []).append(path)

    groups = sorted(
        [members for members in buckets.values() if len(members) >= 2],
        key=len,
        reverse=True,
    )
    unique = [members[0] for members in buckets.values() if len(members) == 1]

    return groups, unique

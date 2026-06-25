from __future__ import annotations


DEFAULT_RRF_RANK_CONSTANT = 60


def reciprocal_rank_score(
    rank: int,
    rank_constant: int = DEFAULT_RRF_RANK_CONSTANT,
) -> float:
    return 1 / (rank_constant + rank)

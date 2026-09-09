from thoughtharbor.search.chunking import chunk_text
from thoughtharbor.search.service import SearchCandidate, rank_candidates


def test_chunking_preserves_exact_source_offsets_and_overlap() -> None:
    text = "First sentence. " + ("Important context " * 30) + " Final sentence."

    chunks = chunk_text(text, max_chars=100, overlap_chars=20)

    assert len(chunks) > 1
    assert all(text[item.start : item.end] == item.text for item in chunks)
    assert chunks[0].start == 0
    assert any(left.end > right.start for left, right in zip(chunks, chunks[1:], strict=True))
    assert chunks[-1].end == len(text)


def test_chunking_rejects_invalid_overlap() -> None:
    try:
        chunk_text("content", max_chars=10, overlap_chars=10)
    except ValueError as error:
        assert "overlap_chars" in str(error)
    else:
        raise AssertionError("invalid overlap must be rejected")


def test_hybrid_ranking_is_provider_independent_and_deterministic() -> None:
    candidates = (
        SearchCandidate(
            chunk_id=2,
            text="lexical match",
            lexical_score=1.0,
            semantic_score=0.2,
            recency_score=1.0,
            source_type_score=1.0,
        ),
        SearchCandidate(
            chunk_id=1,
            text="semantic match",
            lexical_score=0.4,
            semantic_score=1.0,
            recency_score=0.5,
            source_type_score=0.8,
        ),
    )

    ranked = rank_candidates(candidates)

    assert [item.chunk_id for item in ranked] == [1, 2]
    assert ranked[0].score > ranked[1].score


def test_candidate_score_uses_recency_without_accessing_provider() -> None:
    candidate = SearchCandidate(
        chunk_id=1,
        text="source",
        semantic_score=0.0,
        lexical_score=0.0,
        recency_score=1.0,
        source_type_score=0.0,
    )

    assert candidate.score == 0.1

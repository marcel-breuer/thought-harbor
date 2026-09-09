"""Deterministic, provenance-preserving text chunking."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkSlice:
    """One exact slice into the original source string."""

    text: str
    start: int
    end: int


def chunk_text(
    text: str, *, max_chars: int = 1_200, overlap_chars: int = 200
) -> tuple[ChunkSlice, ...]:
    """Split text near semantic boundaries while retaining exact source offsets."""

    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be between zero and max_chars - 1")
    if not text:
        return ()

    slices: list[ChunkSlice] = []
    start = 0
    while start < len(text):
        proposed_end = min(start + max_chars, len(text))
        end = proposed_end
        if proposed_end < len(text):
            boundary_start = start + max_chars // 2
            boundaries = (
                text.rfind("\n\n", boundary_start, proposed_end),
                text.rfind(". ", boundary_start, proposed_end),
                text.rfind("? ", boundary_start, proposed_end),
                text.rfind("! ", boundary_start, proposed_end),
                text.rfind(" ", boundary_start, proposed_end),
            )
            boundary = max(boundaries)
            if boundary >= boundary_start:
                end = boundary + (
                    2 if text[boundary : boundary + 2] in {"\n\n", ". ", "? ", "! "} else 1
                )
        end = max(end, start + 1)
        slices.append(ChunkSlice(text=text[start:end], start=start, end=end))
        if end >= len(text):
            break
        start = max(start + 1, end - overlap_chars)

    return tuple(slices)

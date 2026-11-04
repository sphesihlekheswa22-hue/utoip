"""List pagination helpers."""
from __future__ import annotations

from math import ceil
from typing import Sequence, TypeVar

T = TypeVar("T")

DEFAULT_PER_PAGE = 10


def paginate(
    items: Sequence[T],
    page: int | None = 1,
    per_page: int = DEFAULT_PER_PAGE,
) -> dict:
    """Slice a sequence into a page and return pager metadata."""
    total = len(items)
    per_page = max(1, int(per_page or DEFAULT_PER_PAGE))
    pages = max(1, ceil(total / per_page)) if total else 1
    try:
        page = int(page or 1)
    except (TypeError, ValueError):
        page = 1
    page = max(1, min(page, pages))
    start = (page - 1) * per_page
    chunk = list(items[start : start + per_page])
    # Window of page numbers around current
    window = 5
    half = window // 2
    start_p = max(1, page - half)
    end_p = min(pages, start_p + window - 1)
    start_p = max(1, end_p - window + 1)
    return {
        "items": chunk,
        "page": page,
        "pages": pages,
        "per_page": per_page,
        "total": total,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_page": page - 1 if page > 1 else None,
        "next_page": page + 1 if page < pages else None,
        "page_numbers": list(range(start_p, end_p + 1)),
        "from_idx": start + 1 if total else 0,
        "to_idx": start + len(chunk),
    }

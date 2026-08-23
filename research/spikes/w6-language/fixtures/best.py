"""Inventory helpers for the probe fixture."""


def restock(counts: dict[str, int], sku: str, n: int) -> dict[str, int]:
    """Add n units of sku, refusing negative quantities."""
    try:
        if n < 0:
            raise ValueError("negative restock")
        counts[sku] = counts.get(sku, 0) + n
    except TypeError as exc:
        raise ValueError("bad counts") from exc
    return counts


def test_restock() -> None:
    """Round-trip the happy path."""
    assert restock({}, "a", 2) == {"a": 2}

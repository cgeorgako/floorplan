"""Βοηθητικά μορφοποίησης αριθμών (ελληνική δεκαδική υποδιαστολή = κόμμα)."""
from __future__ import annotations


def fmt(value: float, decimals: int = 2) -> str:
    """Μορφοποίηση με ελληνικό κόμμα (π.χ. 4.5 → '4,50')."""
    return f"{value:.{decimals}f}".replace(".", ",")

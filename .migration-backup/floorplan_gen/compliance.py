"""Έλεγχοι φωτισμού & αερισμού ανά χώρο (Κ.Κ. άρθρα 20 & 21).

Δεσμευτικοί έλεγχοι που ασκεί η ΥΔΟΜ (instructions.md §2.1, §3):
  * Άμεσος φυσικός φωτισμός σε χώρους κύριας χρήσης — άνοιγμα ≥10% καθαρού εμβαδού.
  * Άμεσος φυσικός αερισμός — ανοιγόμενο τμήμα ≥5% καθαρού εμβαδού.
Οι έλεγχοι ελάχιστων εμβαδών/πλευρών (§2.2, Παράρτημα Α) είναι ΜΗ δεσμευτικοί
και σημειώνονται ξεχωριστά ως ποιοτικά κριτήρια.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .layout import _touch_sides
from .models import Category, FloorPlan, Room

GLAZING_HEIGHT = 1.40   # τεκμαρτό ύψος υαλοπίνακα για εκτίμηση επιφάνειας (m)
OPENABLE_FRAC = 0.50    # ποσοστό ανοιγόμενου φύλλου (αερισμός) — συντηρητικά


@dataclass
class ComplianceRow:
    name: str
    category: str
    net_area: float          # καθαρό εμβαδόν (m²)
    main_use: bool
    window_area: float       # εκτιμώμενη επιφάνεια υαλοπίνακα (m²)
    req_light: float         # απαιτούμενο άνοιγμα φωτισμού (m²)
    req_vent: float          # απαιτούμενο ανοιγόμενο αερισμού (m²)
    light_ok: bool
    vent_ok: bool
    note: str = ""


def _window_area(room: Room) -> float:
    total = 0.0
    for op in room.openings:
        if op.kind == "window" and op.to_exterior:
            total += op.width * GLAZING_HEIGHT
    return total


def check_floor(plan: FloorPlan) -> List[ComplianceRow]:
    rows: List[ComplianceRow] = []
    for room in plan.rooms:
        if room.category == Category.CORRIDOR:
            continue
        main = room.category.is_main_use
        area = room.area
        win = _window_area(room)
        req_l = 0.10 * area
        req_v = 0.05 * area
        vent_area = win * OPENABLE_FRAC
        has_ext = bool(_touch_sides(room, plan))

        if main:
            light_ok = win >= req_l - 1e-6 and has_ext
            vent_ok = vent_area >= req_v - 1e-6 and has_ext
        elif room.category in (Category.BATH, Category.WC):
            # βοηθητικοί: επιθυμητός άμεσος αερισμός· αν δεν υπάρχει, τεχνητός.
            light_ok = True
            vent_ok = vent_area >= req_v - 1e-6 or not has_ext
        else:
            light_ok = True
            vent_ok = True

        note = ""
        if main and not has_ext:
            note = "Χωρίς εξωτερικό άνοιγμα — απαιτείται άμεσος φωτισμός/αερισμός."
        elif main and not (light_ok and vent_ok):
            note = "Αύξησε το άνοιγμα (≥10% φως / ≥5% αερισμός)."
        elif room.category in (Category.BATH, Category.WC) and not has_ext:
            note = "Εσωτερικός — απαιτείται τεχνητός αερισμός (Κ.Κ. αρ. 21)."

        rows.append(ComplianceRow(
            room.name, room.category.gr, area, main, win, req_l, req_v,
            light_ok, vent_ok, note))
    return rows


def floor_summary(rows: List[ComplianceRow]) -> str:
    fails = [r for r in rows if r.main_use and not (r.light_ok and r.vent_ok)]
    if not fails:
        return "Όλοι οι χώροι κύριας χρήσης πληρούν φωτισμό ≥10% & αερισμό ≥5%."
    return f"{len(fails)} χώρος/οι κύριας χρήσης χρειάζονται μεγαλύτερο άνοιγμα."

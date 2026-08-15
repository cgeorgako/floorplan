"""Παραγωγή κτιριολογικού προγράμματος (room program) από τα δεδομένα εισόδου.

Οι τιμές-στόχοι εμβαδών και τα ελάχιστα πλάτη αντλούνται από το Παράρτημα Α
του instructions.md (εργονομικά δεδομένα Neufert / NDSS / NKBA) και από τους
εμπειρικούς κανόνες γραφείου §2.2. Είναι ΜΗ δεσμευτικές τιμές ποιότητας — η
τελική διάσταση προκύπτει από την προσαρμογή στο διαθέσιμο περίγραμμα.

Ζώνες προσανατολισμού κατά Παράρτημα Α.6.2 (συμβιβαστική διάταξη Ζώνης Β):
  S  Νότος        → καθιστικό, σαλόνι, τραπεζαρία, κύριο υπνοδωμάτιο
  E  Ανατολή      → κουζίνα, δευτερεύοντα/παιδικά υπνοδωμάτια
  N  Βορράς       → λουτρά, WC, κλιμακοστάσιο, αποθήκη, βεστιάριο, είσοδος
  C  Κέντρο       → διάδρομος (τον προσθέτει η μηχανή διάταξης)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .models import BuildingSpec, Category


@dataclass
class RoomReq:
    """Απαίτηση χώρου προς τοποθέτηση από τη μηχανή διάταξης."""
    category: Category
    name: str
    target_area: float   # επιθυμητό καθαρό εμβαδόν (m²)
    min_width: float     # ελάχιστη καθαρή πλευρά (m)
    zone: str            # 'S' | 'N' | 'E' | 'W' | 'C'
    priority: int = 5    # 1 = υψηλή (τοποθετείται πρώτο)


def _bedroom_reqs(spec: BuildingSpec) -> List[RoomReq]:
    """Δημιουργεί τις απαιτήσεις υπνοδωματίων (1 κύριο + δευτερεύοντα)."""
    reqs: List[RoomReq] = []
    ms = spec.min_bedroom_side
    # Κύριο υπνοδωμάτιο — Νότος/ΝΑ, πλάτος ≥ max(min side, 3,20) (Α.1.3)
    master_w = max(ms, 3.20)
    reqs.append(RoomReq(
        Category.BEDROOM_MASTER, "Κύριο Υπνοδωμάτιο",
        target_area=max(14.0, master_w * ms), min_width=master_w, zone="S", priority=2,
    ))
    # Δευτερεύοντα υπνοδωμάτια — Ανατολή/ΒΑ, πλάτος ≥ min side (≥3,00 όπως ζητά ο χρήστης)
    for i in range(spec.bedrooms - 1):
        reqs.append(RoomReq(
            Category.BEDROOM, f"Υπνοδωμάτιο {i + 2}",
            target_area=max(12.0, ms * ms), min_width=ms, zone="E", priority=3,
        ))
    return reqs


def _service_reqs(spec: BuildingSpec) -> List[RoomReq]:
    """Λουτρά, WC, αποθήκη, βεστιάριο, είσοδος (βοηθητικοί / βόρεια ζώνη)."""
    reqs: List[RoomReq] = []
    for i in range(spec.baths):
        name = "Λουτρό" if spec.baths == 1 else f"Λουτρό {i + 1}"
        # Πλήρες λουτρό 1,80×2,20 = 3,96 m² (Α.2.3)
        reqs.append(RoomReq(Category.BATH, name, target_area=4.0, min_width=1.80,
                            zone="N", priority=4))
    for i in range(spec.wcs):
        name = "WC" if spec.wcs == 1 else f"WC {i + 1}"
        # WC ημέρας άνετο 1,10×1,70 (Α.2.3)
        reqs.append(RoomReq(Category.WC, name, target_area=1.90, min_width=1.10,
                            zone="N", priority=4))
    if spec.has_storage:
        reqs.append(RoomReq(Category.STORAGE, "Αποθήκη", target_area=3.0,
                            min_width=1.20, zone="N", priority=6))
    if spec.has_wardrobe:
        reqs.append(RoomReq(Category.WARDROBE, "Βεστιάριο", target_area=2.5,
                            min_width=1.00, zone="N", priority=6))
    # Χώρος υποδοχής (χωλ) — 1,20×1,50 ελάχ. (Α.5)
    reqs.append(RoomReq(Category.HALL, "Χωλ", target_area=3.0, min_width=1.20,
                        zone="N", priority=1))
    return reqs


def _day_reqs(spec: BuildingSpec) -> List[RoomReq]:
    """Χώροι ημέρας: καθιστικό, σαλόνι, κουζίνα (νότια/ανατολική ζώνη)."""
    reqs: List[RoomReq] = []
    if spec.has_living:
        # Καθιστικό 16–18 m², πλάτος ≥3,20 (§2.2 / Α.4)
        reqs.append(RoomReq(Category.LIVING, "Καθιστικό", target_area=18.0,
                            min_width=3.20, zone="S", priority=2))
    if spec.has_salon:
        reqs.append(RoomReq(Category.SALON, "Σαλόνι", target_area=16.0,
                            min_width=3.20, zone="S", priority=3))
    if spec.has_big_kitchen:
        # Μεγάλη κουζίνα (με τραπεζαρία) — σχήμα Π/νησίδα, πλάτος ≥2,80 (Α.3.5)
        reqs.append(RoomReq(Category.KITCHEN, "Κουζίνα", target_area=12.0,
                            min_width=2.80, zone="E", priority=3))
    else:
        # Απλή κουζίνα 6–8 m², γωνιακή L πλάτος ≥2,20
        reqs.append(RoomReq(Category.KITCHEN, "Κουζίνα", target_area=8.0,
                            min_width=2.20, zone="E", priority=3))
    return reqs


def _stairs_req() -> RoomReq:
    """Κλιμακοστάσιο κατοικίας — καθαρό φρεάτιο ≈2,60×2,20 (§4.4)."""
    return RoomReq(Category.STAIRS, "Κλιμακοστάσιο", target_area=5.7,
                   min_width=2.20, zone="N", priority=1)


def build_program(spec: BuildingSpec) -> List[List[RoomReq]]:
    """Επιστρέφει λίστα προγραμμάτων — μία ανά όροφο.

    Ισόγειο (1 όροφος): ένα ενιαίο πρόγραμμα.
    Διώροφο (2 όροφοι): ζώνη ημέρας κάτω, ζώνη νύχτας πάνω (Α.6.2).
    """
    day = _day_reqs(spec)
    beds = _bedroom_reqs(spec)
    service = _service_reqs(spec)

    if spec.floors == 1:
        program = day + beds + service
        return [program]

    # ── Διώροφο: διαχωρισμός ημέρας/νύχτας ──
    master = [r for r in beds if r.category == Category.BEDROOM_MASTER]
    others = [r for r in beds if r.category == Category.BEDROOM]
    baths = [r for r in service if r.category == Category.BATH]
    wcs = [r for r in service if r.category == Category.WC]
    hall = [r for r in service if r.category == Category.HALL]
    aux = [r for r in service if r.category in (Category.STORAGE, Category.WARDROBE)]

    # Ισόγειο: χώροι ημέρας + είσοδος + 1 WC + αποθήκη + κλιμακοστάσιο
    ground: List[RoomReq] = list(day) + hall + list(aux)
    if wcs:
        ground.append(wcs[0])
    ground.append(_stairs_req())

    # Α' όροφος: υπνοδωμάτια + λουτρά + τυχόν επιπλέον WC + βεστιάριο + κλιμακοστάσιο
    first: List[RoomReq] = master + others + baths + wcs[1:]
    first.append(_stairs_req())

    return [ground, first]

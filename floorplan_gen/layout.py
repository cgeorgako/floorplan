"""Μηχανή διάταξης κατόψεων.

Αρχές (instructions.md + οδηγίες χρήστη):
  * Ο Βορράς είναι πάντα στο επάνω μέρος (+Y)· μακρύς άξονας Α–Δ (§5.3).
  * ΖΩΝΗ ΗΜΕΡΑΣ (νότια) — καθιστικό/σαλόνι/κουζίνα σε **ανοιχτή, συνεχή σειρά**
    με λειτουργική επικοινωνία μεταξύ τους (καθιστικό↔σαλόνι↔κουζίνα).
  * ΖΩΝΗ ΝΥΧΤΑΣ (βόρεια) — υπνοδωμάτια (βόρεια σειρά) + βοηθητικοί (νότια σειρά),
    με **ελάχιστο διάδρομο** ανάμεσά τους (στόχος: ελαχιστοποίηση εμβαδού κυκλοφορίας).
  * Περίγραμμα **πολυγωνικό (Γ/L)** ως προεπιλογή — ορθογωνισμένο, χωρίς καμπύλες·
    ορθογώνιο μόνο αν ζητηθεί ρητά (spec.footprint_shape="rectangular").

Το πολυγωνικό (L) εφαρμόζεται στο ισόγειο μονώροφου. Για διώροφο, το περίγραμμα
τηρείται ορθογώνιο ώστε οι δύο όροφοι να είναι δομικά συνεπείς.
"""
from __future__ import annotations

import math
import random
from dataclasses import replace as dc_replace
from typing import Dict, List, Optional, Tuple

from .models import (
    BuildingSpec, Category, FloorPlan, Opening, Orientation, Proposal, Room,
)
from .program import RoomReq, build_program

DAY_CATEGORIES = [Category.LIVING, Category.SALON, Category.KITCHEN]
MIN_CORRIDOR = 0.95          # ελάχιστο καθαρό πλάτος διαδρόμου (Α.5)
EPS = 1e-4


# ─────────────────────────── Ανοίγματα / πλευρές ──────────────────────────────

def _touch_sides(room: Room, plan: FloorPlan) -> List[str]:
    """Πλευρές του χώρου που εφάπτονται στο εξωτερικό περίβλημα (από ext_sides)."""
    return sorted(room.ext_sides)


def _side_length(room: Room, side: str) -> float:
    return room.w if side in ("N", "S") else room.d


def _add_window(room: Room, side: str) -> None:
    seglen = _side_length(room, side)
    need = max(0.9, 0.10 * room.area / 1.40)      # για υαλοπίνακα ≥10% (ύψος ~1,40)
    width = min(max(need, 0.9), seglen - 0.6)
    if width <= 0.3:
        return
    offset = (seglen - width) / 2.0
    room.openings.append(Opening("window", side, offset, width, to_exterior=True))


def _add_door(room: Room, side: str, width: float = 0.90, kind: str = "door",
              exterior: bool = False) -> None:
    seglen = _side_length(room, side)
    w = min(width, seglen - 0.3)
    if w <= 0.2:
        return
    offset = (seglen - w) / 2.0
    room.openings.append(Opening(kind, side, offset, w, to_exterior=exterior))


# ─────────────────────────── Τοποθέτηση σειράς χώρων ──────────────────────────

def _fit_widths(areas: List[float], mins: List[float], avail: float) -> List[float]:
    """Πλάτη ∝ εμβαδά, με τήρηση ελαχίστων (best-effort) και άθροισμα = avail."""
    n = len(areas)
    if n == 0:
        return []
    tot = sum(areas) or 1.0
    w = [avail * a / tot for a in areas]
    if sum(mins) > avail + 1e-6:
        s = avail / sum(mins)
        return [m * s for m in mins]
    locked = [False] * n
    for _ in range(n + 2):
        deficit = 0.0
        free = 0.0
        for i in range(n):
            if not locked[i] and w[i] < mins[i]:
                deficit += mins[i] - w[i]
                w[i] = mins[i]
                locked[i] = True
        for i in range(n):
            if not locked[i]:
                free += w[i]
        if deficit <= 1e-9 or free <= 1e-9:
            break
        for i in range(n):
            if not locked[i]:
                w[i] -= deficit * (w[i] / free)
    return w


def _place_row(reqs: List[RoomReq], X0: float, X1: float, Y0: float, Y1: float,
               te: float, ti: float, ext: Dict[str, bool], mirror: bool,
               night_x: Optional[Tuple[float, float]] = None) -> List[Room]:
    """Τοποθετεί χώρους σε μία σειρά μέσα στην περιοχή [X0,X1]×[Y0,Y1] (σε
    συντεταγμένες περιγράμματος, με τοίχους). Οι εξωτερικές πλευρές αφήνουν
    πάχος te, οι εσωτερικές ti/2. Ορίζει τα ext_sides κάθε χώρου."""
    if not reqs:
        return []
    ordered = list(reversed(reqs)) if mirror else list(reqs)
    lw = te if ext.get("w") else ti / 2.0
    rw = te if ext.get("e") else ti / 2.0
    n = len(ordered)
    avail = (X1 - X0) - lw - rw - (n - 1) * ti
    if avail <= 0:
        avail = max(0.1, (X1 - X0) - lw - rw)
    widths = _fit_widths([r.target_area for r in ordered],
                         [r.min_width for r in ordered], avail)
    rooms: List[Room] = []
    x = X0 + lw
    for idx, (r, w) in enumerate(zip(ordered, widths)):
        rx0, rx1 = x, x + w
        es = set()
        if ext.get("s"):
            es.add("S")
        if ext.get("n") or (night_x is not None and (rx0 < night_x[0] - 0.05
                            or rx1 > night_x[1] + 0.05)):
            es.add("N")   # ο χώρος βγαίνει εκτός πτέρυγας νύχτας → βόρεια όψη εξωτ.
        if ext.get("w") and idx == 0:
            es.add("W")
        if ext.get("e") and idx == n - 1:
            es.add("E")
        # πάχος τοίχου ΑΝΑ πλευρά του χώρου: εξωτερικός te, εσωτερικός ti/2
        bot = te if "S" in es else ti / 2.0
        top = te if "N" in es else ti / 2.0
        room = Room(r.category, r.name, rx0, Y0 + bot, rx1, Y1 - top)
        room.ext_sides = es
        rooms.append(room)
        x = rx1 + ti
    return rooms


# ─────────────────────────── Διαστασιολόγηση περιγράμματος ────────────────────

def _geometry(spec: BuildingSpec, program: List[RoomReq], shape: str,
              variant: int, force_W: Optional[float] = None,
              force_H: Optional[float] = None) -> dict:
    """Υπολογίζει W, H, Wn, Xn (θέση πτέρυγας νύχτας), Hd, cd και εμβαδά ζωνών.

    `shape`: 'rect' | 'L' | 'T' | 'auto'. Το Xn (οριζόντια μετατόπιση της πτέρυγας
    νύχτας πάνω στη νότια βάση) καθορίζει τον τύπο: Xn=0 → Γ (εσοχή ΒΑ),
    Xn=W-Wn → Γ (εσοχή ΒΔ), κεντραρισμένο → Τ (εσοχές και στις δύο άνω γωνίες).
    Τα force_W/force_H επιβάλλουν εξωτερικές διαστάσεις (συνέπεια ορόφων).
    """
    poly = shape in ("L", "T", "auto")
    te, ti, ms = spec.ext_wall, spec.int_wall, spec.min_bedroom_side
    day = [r for r in program if r.category in DAY_CATEGORIES]
    beds = [r for r in program if r.category in (Category.BEDROOM,
                                                 Category.BEDROOM_MASTER)]
    svc = [r for r in program if r not in day and r not in beds]

    nb = max(1, len(beds))
    day_area = sum(r.target_area for r in day) or 1.0
    bed_area = sum(r.target_area for r in beds) or 1.0
    svc_area = sum(r.target_area for r in svc) or 1.0

    W = force_W if force_W else spec.max_width_ew
    # ελάχιστο καθαρό πλάτος διαδρόμου ≥ MIN_CORRIDOR (cd = clear + ti)
    cd = MIN_CORRIDOR + ti + (0.0, 0.10, 0.05)[variant % 3]

    # Βάθος ζώνης ημέρας· 0 αν δεν υπάρχουν χώροι ημέρας (όροφος υπνοδωματίων)
    if day:
        Hd = _clamp(day_area / W, 3.2, 4.7) * (1.0, 1.05, 0.95)[variant % 3]
    else:
        Hd = 0.0

    # ελάχιστο πλάτος ζώνης νύχτας ώστε ΟΛΑ τα υπνοδωμάτια να τηρούν την ελάχ.
    # πλευρά (χρησιμοποιείται το πραγματικό min_width κάθε υ/δ — το master ζητά 3,20)
    bed_fit = sum(max(r.min_width, ms) for r in beds) + (nb - 1) * ti + 2 * te
    if poly and day:
        Wn = _clamp(bed_fit + 0.5, 0.55 * W, W)
        Wn *= (1.0, 0.9, 1.05)[variant % 3]
        Wn = _clamp(max(Wn, bed_fit), 0.5 * W, W)
    else:
        Wn = W

    bed_w_each = max(ms, (Wn - (nb - 1) * ti - 2 * te) / nb)
    Hb = _clamp(bed_area / (nb * bed_w_each), ms, 4.7)
    Hs = _clamp(svc_area / max(Wn - 2 * te, 1.0), 1.6, 3.2)

    if force_H:
        # επιβολή ύψους (συνέπεια με άλλον όροφο): προσαρμογή βάθους υπνοδωματίων
        H = force_H
        Hb = max(ms, H - Hd - Hs - cd)
    else:
        H = Hd + Hs + cd + Hb
        if H > spec.max_length_ns:
            scale = (spec.max_length_ns - cd) / max(H - cd, 0.1)
            Hd, Hs, Hb = Hd * scale, Hs * scale, Hb * scale
            H = Hd + Hs + cd + Hb

    area = W * Hd + Wn * (Hs + cd + Hb)
    if area > spec.max_total_area and not force_H:
        s = math.sqrt(spec.max_total_area / area)
        W, Wn, Hd, Hs, Hb = W * s, Wn * s, Hd * s, Hs * s, Hb * s
        H = Hd + Hs + cd + Hb

    # Εγγύηση ελάχιστης πλευράς υπνοδωματίων: η ζώνη νύχτας δεν πέφτει κάτω από
    # το bed_fit (τυχόν μικρή υπέρβαση του μέγιστου εμβαδού είναι προτιμότερη).
    Wn = min(W, max(Wn, bed_fit))

    # Θέση πτέρυγας νύχτας (Xn) → τύπος περιγράμματος
    slack = W - Wn
    used = "rect"
    Xn = 0.0
    if poly and day and slack > 0.35:
        pick = shape
        if shape == "auto":                       # «αυτοσχεδιασμός» ανά πρόταση
            pick = ("L", "T", "Lr")[variant % 3]
        if pick == "T":
            Xn, used = slack / 2.0, "T"
        elif pick in ("Lr",) or (pick == "L" and variant % 2):
            Xn, used = slack, "L"                 # εσοχή ΒΔ (Γ κατοπτρικό)
        else:
            Xn, used = 0.0, "L"                    # εσοχή ΒΑ (Γ)

    return {"W": round(W, 3), "H": round(H, 3), "Wn": round(min(Wn, W), 3),
            "Xn": round(Xn, 3), "Hd": round(Hd, 3), "Hs": round(Hs, 3),
            "Hb": round(Hb, 3), "cd": round(cd, 3), "day": day, "beds": beds,
            "svc": svc, "shape": used}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ─────────────────────────────── Διάταξη ορόφου ───────────────────────────────

def layout_floor(spec: BuildingSpec, program: List[RoomReq], floor_label: str,
                 seed: int, entrance: Orientation, shape: str, variant: int = 0,
                 force_W: Optional[float] = None,
                 force_H: Optional[float] = None) -> Tuple[FloorPlan, List[str]]:
    warnings: List[str] = []
    te, ti = spec.ext_wall, spec.int_wall
    g = _geometry(spec, program, shape, variant, force_W, force_H)
    W, H, Wn, Xn = g["W"], g["H"], g["Wn"], g["Xn"]
    Hd, Hs, Hb, cd = g["Hd"], g["Hs"], g["Hb"], g["cd"]
    day, beds, svc = g["day"], g["beds"], g["svc"]
    poly = g["shape"] in ("L", "T") and Wn < W - 0.3 and Hd > 0.3
    if not poly:
        Xn, Wn = 0.0, W
    nx0, nx1 = Xn, Xn + Wn                    # όρια πτέρυγας νύχτας (Α–Δ)
    mirror = bool(variant % 2)

    plan = FloorPlan(floor_label, round(W, 2), round(H, 2), te, ti, entrance=entrance)

    # Όρια ζωνών σε Y (Νότος κάτω → Βορράς πάνω)
    y_day0, y_day1 = 0.0, Hd
    y_svc0, y_svc1 = Hd, Hd + Hs
    y_cor0, y_cor1 = Hd + Hs, Hd + Hs + cd
    y_bed0, y_bed1 = Hd + Hs + cd, H

    rooms: List[Room] = []
    day_rooms: List[Room] = []
    bed_rooms: List[Room] = []
    svc_rooms: List[Room] = []

    # Ζώνη ημέρας (νότια βάση, πλήρες πλάτος W). Όσοι χώροι βγαίνουν εκτός της
    # πτέρυγας νύχτας [nx0,nx1] έχουν βόρεια όψη εξωτερική (εσοχές Γ/Τ).
    if day and Hd > 0.3:
        day_rooms = _place_row(day, 0.0, W, y_day0, y_day1, te, ti,
                               {"s": True, "n": False, "w": True, "e": True},
                               mirror, night_x=((nx0, nx1) if poly else None))
        rooms += day_rooms

    # Ζώνη νύχτας (βόρεια πτέρυγα [nx0,nx1]). Υπνοδωμάτια βόρεια, βοηθητικοί κάτω.
    corridor: Optional[Room] = None
    if beds:
        bed_rooms = _place_row(beds, nx0, nx1, y_bed0, y_bed1, te, ti,
                               {"s": False, "n": True, "w": True, "e": True}, mirror)
        rooms += bed_rooms

    full_depth = Hs + cd
    # ΣΥΜΠΑΓΗΣ ΔΙΑΔΡΟΜΟΣ: δύο βοηθητικοί χώροι πλήρους βάθους στις γωνίες, ο
    # διάδρομος μόνο στο κεντρικό τμήμα (τα ακραία —φαρδιά— υπνοδωμάτια τον
    # φτάνουν από νότο). Ελαχιστοποιεί το μήκος του διαδρόμου.
    compact = bool(beds) and len(svc) >= 2 and cd > 0.05 and Wn > 6.0
    if compact:
        # Οι δύο ΓΩΝΙΑΚΟΙ χώροι (αριστερά/δεξιά) έχουν εξωτερική όψη (Δ/Α) → φως.
        # Προτεραιότητα στα ΛΟΥΤΡΑ (πάντα εξωτ. φως), μετά WC (αν μένει θέση).
        # Ο χωλ & οι στεγνοί χώροι πάνε στο ΚΕΝΤΡΟ (μεταβλητή θέση) — ο χωλ δεν
        # κολλάει πάντα στην άκρη του καθιστικού/σαλονιού.
        baths = [r for r in svc if r.category == Category.BATH]
        wcs = [r for r in svc if r.category == Category.WC]
        dry = [r for r in svc if r.category not in (Category.BATH, Category.WC)]
        light_pri = baths + wcs                 # όσοι θέλουν εξωτ. φως (λουτρά πρώτα)
        corner = light_pri[:2]
        extra_light = light_pri[2:]             # πέραν των 2 γωνιών → κέντρο (εσωτ.)
        # αν λείπουν «φωτεινοί» για τις 2 γωνίες, συμπλήρωσε με στεγνούς
        di = 0
        while len(corner) < 2 and di < len(dry):
            corner.append(dry[di]); di += 1
        dry_mid = dry[di:]
        # μεταβλητή θέση χωλ/στεγνών στο κέντρο ανά πρόταση
        mid_reqs = extra_light + dry_mid
        if mid_reqs:
            k = variant % len(mid_reqs)
            mid_reqs = mid_reqs[k:] + mid_reqs[:k]
        # ποια γωνία αριστερά/δεξιά (εναλλαγή ανά πρόταση για ποικιλία θέσης)
        if len(corner) == 2 and variant % 2:
            corner = [corner[1], corner[0]]
        left_req = corner[0] if corner else None
        right_req = corner[1] if len(corner) > 1 else None
        wl = (_clamp(left_req.target_area / full_depth, left_req.min_width,
                     0.30 * Wn) if left_req else 0.0)
        wr = (_clamp(right_req.target_area / full_depth, right_req.min_width,
                     0.30 * Wn) if right_req else 0.0)
        Xc0 = nx0 + te + (wl + ti if left_req else 0.0)
        Xc1 = nx1 - te - (wr + ti if right_req else 0.0)
        if Xc1 - Xc0 < 1.4 or not left_req:
            compact = False

    if compact:
        left_rooms = _place_row([left_req], nx0, Xc0, y_svc0, y_bed0, te, ti,
                                {"s": False, "n": False, "w": True, "e": False}, False)
        right_rooms = (_place_row([right_req], Xc1, nx1, y_svc0, y_bed0, te, ti,
                       {"s": False, "n": False, "w": False, "e": True}, False)
                       if right_req else [])
        mid_rooms = (_place_row(mid_reqs, Xc0, Xc1, y_svc0, y_svc1, te, ti,
                     {"s": False, "n": False, "w": False, "e": False}, mirror)
                     if mid_reqs else [])
        svc_rooms = left_rooms + mid_rooms + right_rooms
        rooms += svc_rooms
        corridor = Room(Category.CORRIDOR, "Διάδρομος", Xc0 + ti / 2.0,
                        y_cor0 + ti / 2.0, Xc1 - ti / 2.0, y_cor1 - ti / 2.0)
        rooms.append(corridor)
    else:
        # Εφεδρική διάταξη: διάδρομος πλήρους πλάτους ζώνης νύχτας. Τα λουτρά
        # τοποθετούνται στα άκρα (εξωτ. Δ/Α όψη → φυσικό φως).
        if svc:
            baths = [r for r in svc if r.category == Category.BATH]
            rest = [r for r in svc if r.category != Category.BATH]
            ordered = ([baths[0]] if baths else []) + rest
            if len(baths) > 1:
                ordered.append(baths[1])
            for b in baths[2:]:
                ordered.insert(len(ordered) // 2, b)
            svc_rooms = _place_row(ordered, nx0, nx1, y_svc0, y_svc1, te, ti,
                                   {"s": False, "n": False, "w": True, "e": True},
                                   mirror)
            rooms += svc_rooms
        if (bed_rooms or svc_rooms) and cd > 0.05 and nx1 - nx0 - 2 * te > 0.3:
            corridor = Room(Category.CORRIDOR, "Διάδρομος", nx0 + te,
                            y_cor0 + ti / 2.0, nx1 - te, y_cor1 - ti / 2.0)
            rooms.append(corridor)

    plan.rooms = rooms
    if Hd > 0.3:
        plan.cells = [(0.0, 0.0, W, Hd), (nx0, Hd, nx1, H)]
    else:
        plan.cells = [(nx0, 0.0, nx1, H)]
    plan.outline = _outline(W, H, nx0, nx1, Hd) if Hd > 0.3 else \
                   [(nx0, 0.0), (nx1, 0.0), (nx1, H), (nx0, H)]

    _assign_openings(plan, spec, corridor, day_rooms, bed_rooms, svc_rooms,
                     entrance)

    # Παρατηρήσεις ελάχιστης πλευράς υπνοδωματίων
    for r in bed_rooms:
        if min(r.w, r.d) < spec.min_bedroom_side - 0.05:
            warnings.append(
                f"{r.name}: {r.w:.2f}×{r.d:.2f} m — ελάχιστη πλευρά κάτω από "
                f"{spec.min_bedroom_side:.2f} m (στενό περίγραμμα).")
    # Το λουτρό πρέπει ΠΑΝΤΑ να έχει εξωτερικό φυσικό φωτισμό
    for r in svc_rooms:
        if r.category == Category.BATH and not r.ext_sides:
            warnings.append(
                f"{r.name}: χωρίς εξωτερικό άνοιγμα — απαιτείται αναδιάταξη ώστε "
                f"να αποκτήσει φυσικό φωτισμό.")
    return plan, warnings


def _outline(W: float, H: float, nx0: float, nx1: float,
             Hd: float) -> List[Tuple[float, float]]:
    """Ορθογωνισμένο περίγραμμα: νότια βάση [0,W]×[0,Hd] + πτέρυγα νύχτας
    [nx0,nx1]×[Hd,H]. Παράγει Ι/Γ/Τ ανάλογα με τη θέση της πτέρυγας."""
    ln = nx0 > 0.05                      # εσοχή αριστερά (ΒΔ)
    rn = nx1 < W - 0.05                  # εσοχή δεξιά (ΒΑ)
    if not ln and not rn:                # ορθογώνιο
        return [(0.0, 0.0), (W, 0.0), (W, H), (0.0, H)]
    if not ln and rn:                    # Γ, εσοχή ΒΑ
        return [(0.0, 0.0), (W, 0.0), (W, Hd), (nx1, Hd), (nx1, H), (0.0, H)]
    if ln and not rn:                    # Γ, εσοχή ΒΔ
        return [(0.0, 0.0), (W, 0.0), (W, H), (nx0, H), (nx0, Hd), (0.0, Hd)]
    # Τ, εσοχές και στις δύο άνω γωνίες
    return [(0.0, 0.0), (W, 0.0), (W, Hd), (nx1, Hd), (nx1, H), (nx0, H),
            (nx0, Hd), (0.0, Hd)]


# ─────────────────────────────── Ανοίγματα ───────────────────────────────────

def _corridor_door(room: Room, corr: Room, ti: float, dw: float,
                   back: float = 0.10) -> None:
    """Τοποθετεί θύρα στην πλευρά του χώρου που εφάπτεται στον διάδρομο.

    Η θύρα μπαίνει `back` (=0,10 m) πίσω από τον διαχωριστικό τοίχο και όσο πιο
    κοντά γίνεται στο κέντρο του διαδρόμου (ελαχιστοποίηση χρήσιμου μήκους).
    """
    tol = ti * 1.8
    side = None
    lo = hi = 0.0          # διαθέσιμο τμήμα επικάλυψης (σε συντ. πλευράς)
    ccx, ccy = corr.cx, corr.cy
    # οριζόντια επικάλυψη (για θύρες N/S), κατακόρυφη (για E/W)
    ox0, ox1 = max(room.x0, corr.x0), min(room.x1, corr.x1)
    oy0, oy1 = max(room.y0, corr.y0), min(room.y1, corr.y1)
    if abs(room.y0 - corr.y1) < tol and ox1 - ox0 > 0.3:          # διάδρ. νότια
        side, lo, hi, target = "S", ox0 - room.x0, ox1 - room.x0, ccx - room.x0
    elif abs(room.y1 - corr.y0) < tol and ox1 - ox0 > 0.3:        # διάδρ. βόρεια
        side, lo, hi, target = "N", ox0 - room.x0, ox1 - room.x0, ccx - room.x0
    elif abs(room.x1 - corr.x0) < tol and oy1 - oy0 > 0.3:        # διάδρ. ανατ.
        side, lo, hi, target = "E", oy0 - room.y0, oy1 - room.y0, ccy - room.y0
    elif abs(room.x0 - corr.x1) < tol and oy1 - oy0 > 0.3:        # διάδρ. δυτ.
        side, lo, hi, target = "W", oy0 - room.y0, oy1 - room.y0, ccy - room.y0
    if side is None:
        return
    seglen = _side_length(room, side)
    w = min(dw, hi - lo - 2 * back, seglen - 2 * back)
    if w <= 0.2:
        w = min(dw, seglen - 0.2)
    # ομαδοποίηση προς το κέντρο του διαδρόμου, με 0,10 m από τον τοίχο
    ideal = target - w / 2.0
    offset = min(max(ideal, lo + back), hi - back - w)
    offset = min(max(offset, back), seglen - back - w)
    room.openings.append(Opening("door", side, offset, w))


def _assign_openings(plan: FloorPlan, spec: BuildingSpec, corridor: Optional[Room],
                     day_rooms: List[Room], bed_rooms: List[Room],
                     svc_rooms: List[Room], entrance: Orientation) -> None:
    door_w = {Category.BATH: 0.80, Category.WC: 0.70, Category.STORAGE: 0.80,
              Category.WARDROBE: 0.80}

    # Παράθυρα (κύρια χρήση + λουτρά/wc) στην καλύτερη εξωτ. πλευρά (Ν>Α>Β>Δ)
    pref = {"S": 0, "E": 1, "N": 2, "W": 3}
    for room in plan.rooms:
        if room.category in (Category.CORRIDOR, Category.STAIRS):
            continue
        if not (room.category.is_main_use or room.category in (Category.BATH,
                                                               Category.WC)):
            continue
        sides = sorted(room.ext_sides, key=lambda s: pref[s])
        if sides:
            _add_window(room, sides[0])

    # Λειτουργική επικοινωνία ζώνης ημέρας: ανοιχτά περάσματα μεταξύ διαδοχικών
    # χώρων (καθιστικό↔σαλόνι↔κουζίνα) — κανόνες 4 & 5.
    ordered_day = sorted(day_rooms, key=lambda r: r.x0)
    for a, b in zip(ordered_day, ordered_day[1:]):
        depth = min(a.d, b.d)
        w = min(1.60, max(1.10, depth - 0.6))
        # άνοιγμα στο κοινό κατακόρυφο τοίχωμα (a δεξιά πλευρά)
        seg = min(a.d, b.d)
        off = (a.d - w) / 2.0
        a.openings.append(Opening("opening", "E", off, w))

    # Θύρες προς τον διάδρομο: στην πλευρά κάθε χώρου που εφάπτεται στον
    # διάδρομο, τοποθετημένες 0,10 m πίσω από τον διαχωριστικό τοίχο (αίτημα
    # χρήστη) και ομαδοποιημένες προς το κέντρο του διαδρόμου.
    if corridor is not None:
        for room in bed_rooms + svc_rooms:
            _corridor_door(room, corridor, plan.int_wall,
                           door_w.get(room.category, 0.90))

    # Σύνδεση ζώνης ημέρας ↔ διαδρόμου: μέσω του χωλ αν υπάρχει· αλλιώς μέσω
    # στεγνού βοηθητικού (αποθήκη/βεστιάριο) — ΠΟΤΕ μέσα από λουτρό/WC.
    hall = next((r for r in svc_rooms if r.category == Category.HALL), None)
    connector = hall or next(
        (r for r in svc_rooms if r.category in (Category.STORAGE,
         Category.WARDROBE)), None) or next(
        (r for r in svc_rooms if r.category not in (Category.BATH, Category.WC)),
        None)
    if connector is not None and day_rooms:
        _add_door(connector, "S", 0.90)

    # Θύρα εισόδου στην όψη του ζητούμενου προσανατολισμού
    ent = entrance.value if entrance else "S"
    preford = {Category.HALL: 0, Category.LIVING: 1, Category.SALON: 2,
               Category.KITCHEN: 3, Category.CORRIDOR: 4}
    W, H = plan.width_ew, plan.length_ns
    cand = [r for r in plan.rooms
            if ent in r.ext_sides and r.category != Category.STAIRS]

    def _centr(r: Room) -> float:
        return abs(r.cx - W / 2) if ent in ("N", "S") else abs(r.cy - H / 2)

    if cand:
        cand.sort(key=lambda r: (preford.get(r.category, 9), _centr(r)))
        _add_door(cand[0], ent, 1.00, exterior=True)
    else:
        target = next((r for r in plan.rooms if r.category in (
            Category.HALL, Category.LIVING, Category.SALON)), None)
        if target and target.ext_sides:
            _add_door(target, sorted(target.ext_sides)[0], 1.00, exterior=True)


# ─────────────────────────── Μικτές διαστάσεις χώρου ──────────────────────────

def room_gross_dims(room: Room, plan: FloorPlan) -> Tuple[float, float]:
    """Μικτές διαστάσεις (καθαρές + πλήρης εξωτ. τοίχος ή μισός εσωτερικός)."""
    te, ti = plan.ext_wall, plan.int_wall
    s = room.ext_sides
    left = te if "W" in s else ti / 2.0
    right = te if "E" in s else ti / 2.0
    bottom = te if "S" in s else ti / 2.0
    top = te if "N" in s else ti / 2.0
    return room.w + left + right, room.d + bottom + top


# ─────────────────────────── Επιλογή & παραγωγή ──────────────────────────────

def generate_proposals(spec: BuildingSpec) -> List[Proposal]:
    errs = spec.validate()
    if errs:
        raise ValueError("Σφάλματα δεδομένων:\n- " + "\n- ".join(errs))

    floor_labels = (["Ισόγειο"] if spec.floors == 1 else ["Ισόγειο", "Α' Όροφος"])
    # Πολυγωνικό (Γ/Τ) μόνο σε μονώροφο· σε διώροφο ορθογώνιο (δομική συνέπεια).
    shape = spec.shape_mode() if spec.floors == 1 else "rect"

    proposals: List[Proposal] = []
    for i in range(spec.num_proposals):
        seed = 1000 + i * 37
        # Ο χωλ (αν επιλεγεί) ΔΕΝ μπαίνει σε όλες τις λύσεις — εναλλάσσεται.
        include_hall = spec.has_hall and (i % 3 != 1)
        program_floors = build_program(spec, include_hall)
        prop = Proposal(index=i + 1, spec=spec, seed=seed)
        base_W = base_H = None
        for fl_idx, program in enumerate(program_floors):
            plan, warns = layout_floor(
                spec, program, floor_labels[fl_idx], seed + fl_idx,
                spec.entrance, shape, variant=i, force_W=base_W, force_H=base_H)
            if fl_idx == 0:            # δομική συνέπεια: οι επόμενοι όροφοι
                base_W = plan.width_ew  # ακολουθούν το εξωτ. περίγραμμα του ισογείου
                base_H = plan.length_ns
            prop.floors.append(plan)
            for wn in warns:
                tag = f"[{floor_labels[fl_idx]}] {wn}"
                if tag not in prop.warnings:
                    prop.warnings.append(tag)
        proposals.append(prop)
    return proposals

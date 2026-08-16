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


# Ελεύθερη απόσταση ανοίγματος από κάθετο (διαχωριστικό) τοίχο — κανένα άνοιγμα
# δεν «πέφτει» πάνω σε κάθετο τοίχο.
_OPEN_CLR = 0.12


def _add_window(room: Room, side: str) -> None:
    seglen = _side_length(room, side)
    need = max(0.9, 0.10 * room.area / 1.40)      # για υαλοπίνακα ≥10% (ύψος ~1,40)
    width = min(max(need, 0.9), seglen - 2 * _OPEN_CLR)
    if width <= 0.3:
        return
    offset = (seglen - width) / 2.0               # κεντραρισμένο → μακριά από γωνίες
    room.openings.append(Opening("window", side, offset, width, to_exterior=True))


def _add_door(room: Room, side: str, width: float = 0.90, kind: str = "door",
              exterior: bool = False) -> None:
    seglen = _side_length(room, side)
    w = min(width, seglen - 2 * _OPEN_CLR)
    if w <= 0.2:
        return
    offset = (seglen - w) / 2.0
    # εξασφάλισε ελεύθερη απόσταση ≥ _OPEN_CLR από τους κάθετους τοίχους
    offset = min(max(offset, _OPEN_CLR), seglen - _OPEN_CLR - w)
    room.openings.append(Opening(kind, side, offset, w, to_exterior=exterior))


# ─────────────────────────── Τοποθέτηση σειράς χώρων ──────────────────────────

def _fit_widths(areas: List[float], mins: List[float], avail: float,
                weights: Optional[List[float]] = None,
                maxes: Optional[List[Optional[float]]] = None) -> List[float]:
    """Πλάτη = ελάχιστο + κατανομή πλεονάζοντος κατά `weights` (προεπιλογή:
    ανάλογα με το εμβαδόν). Τηρούνται ελάχιστα και (προαιρετικά) μέγιστα (max_side).
    """
    n = len(areas)
    if n == 0:
        return []
    if sum(mins) > avail + 1e-6:              # δεν χωρούν ούτε τα ελάχιστα
        s = avail / sum(mins)
        return [m * s for m in mins]
    w = weights if weights else areas
    w = [max(1e-6, v) for v in w]
    extra = avail - sum(mins)
    sw = sum(w)
    widths = [mins[i] + extra * w[i] / sw for i in range(n)]
    # εφαρμογή μέγιστων πλευρών (π.χ. αποθήκη ≤ 2,00 μ.): cap & ανακατανομή
    if maxes and any(m is not None for m in maxes):
        capped = [False] * n
        for _ in range(n + 2):
            excess = 0.0
            for i in range(n):
                if (maxes[i] is not None and not capped[i]
                        and widths[i] > maxes[i] + 1e-9):
                    excess += widths[i] - maxes[i]
                    widths[i] = maxes[i]
                    capped[i] = True
            if excess <= 1e-9:
                break
            fw = sum(w[i] for i in range(n) if not capped[i])
            if fw <= 1e-9:
                break
            for i in range(n):
                if not capped[i]:
                    widths[i] += excess * w[i] / fw
    return widths


def _place_row(reqs: List[RoomReq], X0: float, X1: float, Y0: float, Y1: float,
               te: float, ti: float, ext: Dict[str, bool], mirror: bool,
               night_x: Optional[Tuple[float, float]] = None,
               day_x: Optional[Tuple[float, float]] = None) -> List[Room]:
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
                         [r.min_width for r in ordered], avail,
                         weights=[r.grow * r.target_area for r in ordered],
                         maxes=[r.max_side for r in ordered])
    rooms: List[Room] = []
    x = X0 + lw
    for idx, (r, w) in enumerate(zip(ordered, widths)):
        rx0, rx1 = x, x + w
        es = set()
        # Νότια όψη εξωτερική εκτός αν ο χώρος καλύπτεται πλήρως από τη νότια βάση
        # ημέρας (κλιμακωτό Z: τμήμα ζώνης νύχτας εκτός βάσης → όψη προς ύπαιθρο).
        if ext.get("s") or (day_x is not None and not (
                day_x[0] - 0.05 <= rx0 and rx1 <= day_x[1] + 0.05)):
            es.add("S")
        # Βόρεια όψη εξωτερική εκτός αν ο χώρος βρίσκεται ΕΞ ΟΛΟΚΛΗΡΟΥ κάτω από την
        # πτέρυγα νύχτας. Αν «πατάει» έστω και εν μέρει στην εσοχή (Γ/Τ), η βόρεια
        # όψη βλέπει στο ύπαιθρο → εξωτερικός τοίχος (te). Μόνο όταν καλύπτεται
        # πλήρως από την πτέρυγα παραμένει εσωτερική (ti).
        if ext.get("n") or (night_x is not None and not (
                night_x[0] - 0.05 <= rx0 and rx1 <= night_x[1] + 0.05)):
            es.add("N")
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
    poly = shape in ("L", "T", "Z", "auto")
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

    has_salon = any(r.category == Category.SALON for r in day)
    has_storage = any(r.category == Category.STORAGE for r in svc)
    allow = te + ti / 2.0                 # ανοχή τοίχων: καθαρή = μικτή − allow
    # Στόχοι ΒΑΘΟΥΣ (καθαρή διάσταση + ανοχή): σαλόνι & master ≥ 3,50 μ.
    day_min_d = (3.50 if has_salon else 3.20) + allow
    bed_min_d = max(ms, 3.50) + allow
    day_floor = (3.00 + allow) if day else 0.0    # απόλυτο κατώφλι βάθους ημέρας

    Hd = max(_clamp(day_area / W, day_min_d, 4.9 + allow)
             * (1.0, 1.05, 0.95)[variant % 3], day_min_d) if day else 0.0

    # ελάχ. πλάτος ζώνης νύχτας ώστε ΟΛΑ τα υπνοδωμάτια να τηρούν την ελάχ. πλευρά
    bed_fit = sum(max(r.min_width, ms) for r in beds) + (nb - 1) * ti + 2 * te
    if poly and day:
        Wn = _clamp(bed_fit + 0.5, 0.55 * W, W) * (1.0, 0.9, 1.05)[variant % 3]
        Wn = _clamp(max(Wn, bed_fit), 0.5 * W, W)
    else:
        Wn = W

    bed_w_each = max(ms, (Wn - (nb - 1) * ti - 2 * te) / nb)
    Hb = max(_clamp(bed_area / (nb * bed_w_each), bed_min_d, 4.9 + allow), bed_min_d)
    hs_max = (2.0 + ti) if has_storage else 3.2   # αποθήκη ≤2,00 μ. καθαρό βάθος
    Hs = _clamp(svc_area / max(Wn - 2 * te, 1.0), 1.6, hs_max)

    if force_H:
        H = force_H
        Hb = max(bed_min_d, H - Hd - Hs - cd)
    else:
        H = Hd + Hs + cd + Hb
        if H > spec.max_length_ns:
            # ΠΡΟΤΕΡΑΙΟΤΗΤΑ: (α) υπνοδωμάτια → (β) διάδρομος → (γ) σαλόνι/καθιστικό.
            # Μειώνουμε πρώτα το βάθος ημέρας (γ), μετά βοηθητικούς, τελευταία υ/δ.
            over = H - spec.max_length_ns
            for lo, key in (("Hd", day_floor), ("Hs", 1.5), ("Hb", 3.00 + allow)):
                val = {"Hd": Hd, "Hs": Hs, "Hb": Hb}[lo]
                cut = min(over, max(val - key, 0.0))
                if lo == "Hd":
                    Hd -= cut
                elif lo == "Hs":
                    Hs -= cut
                else:
                    Hb -= cut
                over -= cut
                if over <= 1e-6:
                    break
            H = Hd + Hs + cd + Hb

    # Μέγιστο εμβαδόν: μείωση ΠΛΑΤΟΥΣ (διατηρεί τα βάθη → προτεραιότητες αναλλοίωτες)
    gross = W * Hd + Wn * (Hs + cd + Hb)
    if gross > spec.max_total_area and not force_H and gross > 0:
        f = spec.max_total_area / gross
        W, Wn = W * f, Wn * f
    Wn = min(W, max(Wn, bed_fit))

    # Θέση πτέρυγας νύχτας (Xn) → τύπος περιγράμματος
    slack = W - Wn
    used = "rect"
    Xn = 0.0
    Xd = 0.0                                       # μετατόπιση νότιας βάσης (Z)
    if poly and day and slack > 0.35:
        pick = shape
        if shape == "auto":                       # «αυτοσχεδιασμός» ανά πρόταση
            pick = ("L", "T", "Z", "Lr")[variant % 4]
        if pick == "T":
            Xn, used = slack / 2.0, "T"
        elif pick == "Z":
            # Κλιμακωτό (Z): πτέρυγα νύχτας αριστερά (εσοχή ΒΑ) + νότια βάση
            # δεξιά (εσοχή ΝΔ) → εσοχές σε διαγώνια αντίθετες γωνίες. Εφαρμόζεται
            # μόνο αν τα δωμάτια ημέρας χωρούν στη στενότερη βάση.
            day_fit = (sum(r.min_width for r in day) + (len(day) - 1) * ti
                       + 2 * te)
            room_notch = min(slack, W - day_fit - 0.30)
            if room_notch > 0.5:
                Xn, Xd, used = 0.0, room_notch, "Z"
            else:
                Xn, used = 0.0, "L"                # πολύ στενή βάση → πτώση σε Γ
        elif pick in ("Lr",) or (pick == "L" and variant % 2):
            Xn, used = slack, "L"                 # εσοχή ΒΔ (Γ κατοπτρικό)
        else:
            Xn, used = 0.0, "L"                    # εσοχή ΒΑ (Γ)

    return {"W": round(W, 3), "H": round(H, 3), "Wn": round(min(Wn, W), 3),
            "Xn": round(Xn, 3), "Xd": round(Xd, 3), "Hd": round(Hd, 3),
            "Hs": round(Hs, 3), "Hb": round(Hb, 3), "cd": round(cd, 3),
            "day": day, "beds": beds, "svc": svc, "shape": used}


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
    Xd = g.get("Xd", 0.0)
    Hd, Hs, Hb, cd = g["Hd"], g["Hs"], g["Hb"], g["cd"]
    day, beds, svc = g["day"], g["beds"], g["svc"]
    poly = g["shape"] in ("L", "T", "Z") and Wn < W - 0.3 and Hd > 0.3
    if not poly:
        Xn, Wn = 0.0, W
    if g["shape"] != "Z" or not poly:
        Xd = 0.0
    dx0, dx1 = Xd, W                          # όρια νότιας βάσης ημέρας (Α–Δ)
    nx0, nx1 = Xn, Xn + Wn                    # όρια πτέρυγας νύχτας (Α–Δ)
    day_x = (dx0, dx1) if Xd > 0.05 else None   # για σήμανση νότιας όψης (Z)
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
        day_rooms = _place_row(day, dx0, dx1, y_day0, y_day1, te, ti,
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
    # φτάνουν από νότο). Απαιτεί ≥3 βοηθητικούς (2 γωνίες + ≥1 κεντρικό) ώστε να
    # ΜΗΝ μένει κενή (γκρι) ζώνη στο κέντρο· αλλιώς πλήρης διάταξη (fallback).
    compact = bool(beds) and len(svc) >= 3 and cd > 0.05 and Wn > 6.0
    if compact:
        # Οι δύο ΓΩΝΙΑΚΟΙ χώροι (αριστερά/δεξιά) έχουν εξωτερική όψη (Δ/Α) → φως.
        # Προτεραιότητα στα ΛΟΥΤΡΑ (πάντα εξωτ. φως), μετά WC (αν μένει θέση).
        # Ο χωλ & οι στεγνοί χώροι πάνε στο ΚΕΝΤΡΟ (μεταβλητή θέση) — ο χωλ δεν
        # κολλάει πάντα στην άκρη του καθιστικού/σαλονιού.
        baths = [r for r in svc if r.category == Category.BATH]
        wcs = [r for r in svc if r.category == Category.WC]
        dry = [r for r in svc if r.category not in (Category.BATH, Category.WC)]
        # η αποθήκη (max 2,00 μ.) ΔΕΝ πάει σε γωνία πλήρους βάθους → τελευταία
        dry.sort(key=lambda r: 1 if r.category == Category.STORAGE else 0)
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
                                {"s": False, "n": False, "w": True, "e": False},
                                False, day_x=day_x)
        right_rooms = (_place_row([right_req], Xc1, nx1, y_svc0, y_bed0, te, ti,
                       {"s": False, "n": False, "w": False, "e": True}, False,
                       day_x=day_x)
                       if right_req else [])
        mid_rooms = (_place_row(mid_reqs, Xc0, Xc1, y_svc0, y_svc1, te, ti,
                     {"s": False, "n": False, "w": False, "e": False}, mirror,
                     day_x=day_x)
                     if mid_reqs else [])
        svc_rooms = left_rooms + mid_rooms + right_rooms
        rooms += svc_rooms
        corridor = Room(Category.CORRIDOR, "Διάδρομος", Xc0 + ti / 2.0,
                        y_cor0 + ti / 2.0, Xc1 - ti / 2.0, y_cor1 - ti / 2.0)
        rooms.append(corridor)
        # Αν οι κεντρικοί βοηθητικοί (με μέγιστες διαστάσεις) ΔΕΝ γεμίζουν τη ζώνη
        # τους, ΜΗΝ αφήνεις γκρι νεκρή ζώνη: προέκτεινε τον διάδρομο (λευκή
        # κυκλοφορία) προς τα κάτω στο κενό, δεξιά των βοηθητικών.
        xm = max((r.x1 for r in mid_rooms), default=Xc0)
        gap_x0 = xm + ti / 2.0
        if (Xc1 - ti / 2.0) - gap_x0 > 0.4:
            fill = Room(Category.CORRIDOR, "", gap_x0, y_svc0 + ti / 2.0,
                        Xc1 - ti / 2.0, y_cor0 + ti / 2.0)
            rooms.append(fill)
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
                                   mirror, day_x=day_x)
            rooms += svc_rooms
        if (bed_rooms or svc_rooms) and cd > 0.05 and nx1 - nx0 - 2 * te > 0.3:
            corridor = Room(Category.CORRIDOR, "Διάδρομος", nx0 + te,
                            y_cor0 + ti / 2.0, nx1 - te, y_cor1 - ti / 2.0)
            rooms.append(corridor)

    plan.rooms = rooms
    if Hd > 0.3:
        plan.cells = [(dx0, 0.0, dx1, Hd), (nx0, Hd, nx1, H)]
        plan.outline = _outline_stack(dx0, dx1, nx0, nx1, Hd, H)
    else:
        plan.cells = [(nx0, 0.0, nx1, H)]
        plan.outline = [(nx0, 0.0), (nx1, 0.0), (nx1, H), (nx0, H)]

    _assign_openings(plan, spec, corridor, day_rooms, bed_rooms, svc_rooms,
                     entrance)

    # Παρατηρήσεις ελάχιστης πλευράς υπνοδωματίων
    for r in bed_rooms:
        thr = 3.50 if r.category == Category.BEDROOM_MASTER else spec.min_bedroom_side
        if min(r.w, r.d) < thr - 0.05:
            warnings.append(
                f"{r.name}: {r.w:.2f}×{r.d:.2f} m — ελάχιστη πλευρά κάτω από "
                f"{thr:.2f} m (στενό περίγραμμα).")
    # Σαλόνι: ελάχιστη διάσταση 3,50 μ.
    for r in day_rooms:
        if r.category == Category.SALON and min(r.w, r.d) < 3.50 - 0.05:
            warnings.append(
                f"Σαλόνι: {r.w:.2f}×{r.d:.2f} m — ελάχ. διάσταση κάτω από 3,50 m· "
                f"αυξήστε το μήκος (Β–Ν) του περιγράμματος.")
    for r in svc_rooms:
        # Το λουτρό πρέπει ΠΑΝΤΑ να έχει εξωτερικό φυσικό φωτισμό
        if r.category == Category.BATH and not r.ext_sides:
            warnings.append(
                f"{r.name}: χωρίς εξωτερικό άνοιγμα — απαιτείται αναδιάταξη ώστε "
                f"να αποκτήσει φυσικό φωτισμό.")
        # Αποθήκη ≤ 2,00 μ. σε κάθε κατεύθυνση
        if r.category == Category.STORAGE and max(r.w, r.d) > 2.02:
            warnings.append(
                f"Αποθήκη: {r.w:.2f}×{r.d:.2f} m — υπερβαίνει το μέγιστο 2,00 m.")
    return plan, warnings


def _outline_stack(dx0: float, dx1: float, nx0: float, nx1: float,
                   Hd: float, H: float) -> List[Tuple[float, float]]:
    """Γενικό ορθογωνισμένο περίγραμμα ένωσης δύο στοιβαγμένων ορθογωνίων: νότια
    βάση ημέρας [dx0,dx1]×[0,Hd] + πτέρυγα νύχτας [nx0,nx1]×[Hd,H]. Παράγει
    I/Γ/Τ (όταν dx0=0, dx1=W) ή κλιμακωτό Z (όταν η βάση είναι μετατοπισμένη),
    αφαιρώντας τυχόν εκφυλισμένες (συνευθειακές) κορυφές."""
    # CCW περίγραμμα ένωσης: κάτω βάση → δεξιά ακμή → σκαλί στο Hd → πτέρυγα →
    # σκαλί επιστροφής → αριστερή ακμή. Οι εκφυλισμένες κορυφές (όταν οι ακμές
    # ταυτίζονται, π.χ. ορθογώνιο/Γ) αφαιρούνται στη συνέχεια.
    pts: List[Tuple[float, float]] = [
        (dx0, 0.0), (dx1, 0.0), (dx1, Hd), (nx1, Hd),
        (nx1, H), (nx0, H), (nx0, Hd), (dx0, Hd)]
    # καθάρισμα συνευθειακών/διπλών κορυφών
    out: List[Tuple[float, float]] = []
    for p in pts:
        if not out or abs(out[-1][0] - p[0]) > 1e-6 or abs(out[-1][1] - p[1]) > 1e-6:
            out.append(p)
    while len(out) > 3:
        removed = False
        i = 0
        while i < len(out):
            a, b, cc = out[i - 1], out[i], out[(i + 1) % len(out)]
            if (abs(a[0] - b[0]) < 1e-6 and abs(b[0] - cc[0]) < 1e-6) or \
               (abs(a[1] - b[1]) < 1e-6 and abs(b[1] - cc[1]) < 1e-6):
                out.pop(i)                # συνευθειακή → αφαίρεση
                removed = True
            else:
                i += 1
        if not removed:
            break
    return out


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

    # ── Έλεγχος προσβασιμότητας: ΚΑΘΕ χώρος πρέπει να έχει επικοινωνία (θύρα/
    # άνοιγμα). Όσοι έμειναν χωρίς άνοιγμα αποκτούν θύρα προς γειτονικό χώρο (ή,
    # ως έσχατη λύση, εξωτερική θύρα).
    _ensure_access(plan)


def _shared_wall(a: Room, b: Room, ti: float) -> Optional[Tuple[str, float, float]]:
    """Επιστρέφει (πλευρά του a, lo, hi) του κοινού διαχωριστικού τοίχου a↔b, ή
    None αν δεν εφάπτονται σε επαρκές μήκος (≥0,60 μ.)."""
    tol = ti * 1.8 + 1e-6
    ox0, ox1 = max(a.x0, b.x0), min(a.x1, b.x1)
    oy0, oy1 = max(a.y0, b.y0), min(a.y1, b.y1)
    if abs(a.y1 - b.y0) < tol and ox1 - ox0 > 0.6:      # b βόρεια του a
        return "N", ox0 - a.x0, ox1 - a.x0
    if abs(a.y0 - b.y1) < tol and ox1 - ox0 > 0.6:      # b νότια του a
        return "S", ox0 - a.x0, ox1 - a.x0
    if abs(a.x1 - b.x0) < tol and oy1 - oy0 > 0.6:      # b ανατολικά του a
        return "E", oy0 - a.y0, oy1 - a.y0
    if abs(a.x0 - b.x1) < tol and oy1 - oy0 > 0.6:      # b δυτικά του a
        return "W", oy0 - a.y0, oy1 - a.y0
    return None


def _ensure_access(plan: FloorPlan) -> None:
    """Εγγυάται ότι κάθε χώρος (πλην κλίμακας) έχει τουλάχιστον ένα άνοιγμα."""
    ti = plan.int_wall
    for room in plan.rooms:
        if room.category == Category.STAIRS or room.openings:
            continue
        # 1) θύρα προς τον πλησιέστερο γειτονικό εσωτερικό χώρο
        placed = False
        others = [r for r in plan.rooms if r is not room
                  and r.category != Category.STAIRS]
        others.sort(key=lambda r: abs(r.cx - room.cx) + abs(r.cy - room.cy))
        for other in others:
            sw = _shared_wall(room, other, ti)
            if sw is None:
                continue
            side, lo, hi = sw
            seglen = _side_length(room, side)
            dw = 0.80 if room.category in (Category.BATH, Category.WC) else 0.90
            w = min(dw, hi - lo - 0.20, seglen - 0.20)
            if w <= 0.2:
                continue
            offset = min(max((lo + hi) / 2.0 - w / 2.0, lo + 0.10),
                         hi - 0.10 - w)
            offset = min(max(offset, 0.10), seglen - 0.10 - w)
            room.openings.append(Opening("door", side, offset, w))
            placed = True
            break
        # 2) έσχατη λύση: εξωτερική θύρα σε διαθέσιμη εξωτερική πλευρά
        if not placed and room.ext_sides:
            _add_door(room, sorted(room.ext_sides)[0], 0.90, exterior=True)


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

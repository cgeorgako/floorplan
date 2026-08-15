"""Μηχανή διάταξης κατόψεων (banded tiling).

Αρχή λειτουργίας — «ζωνική διάταξη»:
  * Ο Βορράς είναι πάντα στο επάνω μέρος (+Y). Ο μακρύς άξονας τοποθετείται
    κατά Α–Δ (instructions.md §5.3), εντός του μέγιστου περιγράμματος.
  * Η κάτοψη χωρίζεται σε ΖΩΝΗ ΗΜΕΡΑΣ (νότια, κάτω) και ΖΩΝΗ ΝΥΧΤΑΣ/ΒΟΗΘΗΤΙΚΩΝ
    (βόρεια, πάνω), με ενδιάμεσο ΔΙΑΔΡΟΜΟ που εξασφαλίζει την κυκλοφορία και τη
    διάκριση ζώνης ημέρας/νύχτας (Α.6.2).
  * Κάθε ζώνη «στρώνεται» με χώρους σε μία σειρά (πλάτη ∝ επιθυμητό εμβαδόν),
    ώστε η κάτοψη να είναι πλήρως συμπληρωμένη (tiled), χωρίς επικαλύψεις.
  * Οι εξωτερικοί τοίχοι (πάχος te) περιβάλλουν το κτίριο· οι εσωτερικοί (πάχος
    ti) καταλαμβάνουν τα διάκενα μεταξύ χώρων.

Η ποικιλία μεταξύ προτάσεων προκύπτει από παραμέτρους ελεγχόμενες με seed:
λόγο βάθους ζωνών, πλάτος διαδρόμου, κατοπτρισμό, μικρή μεταβολή περιγράμματος
και σειρά χώρων.
"""
from __future__ import annotations

import math
import random
from dataclasses import replace as dc_replace
from typing import List, Optional, Tuple

from .models import (
    BuildingSpec, Category, FloorPlan, Opening, Orientation, Proposal, Room,
)
from .program import RoomReq, build_program

# Κατηγορίες της νότιας ζώνης ΗΜΕΡΑΣ (φως/θέα/χειμ. ηλιακό κέρδος). Τα
# υπνοδωμάτια εντάσσονται στη βόρεια ζώνη ΝΥΧΤΑΣ (Α.6.1 «Σχολή Α» για Ζώνη Β:
# δροσερά υπνοδωμάτια & ζώνη θερμικής ανάσχεσης), ώστε να υπάρχει καθαρή
# διάκριση ζώνης ημέρας/νύχτας (Α.6.2).
SOUTH_CATEGORIES = {
    Category.LIVING, Category.SALON, Category.KITCHEN,
}
MIN_CORRIDOR = 0.95        # ελάχιστο καθαρό πλάτος διαδρόμου (Α.5)
MIN_ROOM_DEPTH = 2.10      # ελάχιστο βάθος βοηθητικής ζώνης
CIRC_FRACTION = 0.12       # στόχος επιφάνειας κυκλοφορίας (Α.6.2: 10–14%)
WALL_FRACTION = 0.14       # προσαύξηση τοίχων (Α.7: 12–15%)


# ─────────────────────────── Squarified treemap ──────────────────────────────

def _worst_ratio(row: List[float], length: float) -> float:
    """Χειρότερος λόγος πλευρών (aspect) μιας σειράς treemap κατά μήκος `length`."""
    s = sum(row)
    if s <= 0 or length <= 0:
        return float("inf")
    rmax, rmin = max(row), min(row)
    return max((length * length * rmax) / (s * s), (s * s) / (length * length * rmin))


def _squarify(vals: List[float], x: float, y: float, w: float, h: float,
              out: List[Tuple[float, float, float, float]]) -> None:
    """Squarified treemap (Bruls κ.ά.). Τα vals έχουν άθροισμα = w·h.

    Γεμίζει το ορθογώνιο με υπο-ορθογώνια κοντά στο τετράγωνο, στη σειρά των vals.
    """
    if not vals:
        return
    if len(vals) == 1:
        out.append((x, y, w, h))
        return
    short = min(w, h)
    i = 1
    best = _worst_ratio(vals[:1], short)
    while i < len(vals):
        cand = _worst_ratio(vals[:i + 1], short)
        if cand <= best:
            best = cand
            i += 1
        else:
            break
    row = vals[:i]
    s = sum(row)
    if w >= h:                       # στήλη αριστερά, πλάτος cw
        cw = s / h if h > 0 else w
        yy = y
        for a in row:
            rh = a / cw if cw > 0 else 0.0
            out.append((x, yy, cw, rh))
            yy += rh
        _squarify(vals[i:], x + cw, y, w - cw, h, out)
    else:                            # σειρά κάτω, ύψος ch
        ch = s / w if w > 0 else h
        xx = x
        for a in row:
            rw = a / ch if ch > 0 else 0.0
            out.append((xx, y, rw, ch))
            xx += rw
        _squarify(vals[i:], x, y + ch, w, h - ch, out)


def _place_band(reqs: List[RoomReq], x0: float, x1: float, y0: float, y1: float,
                ti: float, mirror: bool,
                interior: Tuple[float, float, float, float]) -> Tuple[List[Room], bool]:
    """Τοποθετεί χώρους σε μια ζώνη [x0,x1]×[y0,y1] με squarified treemap.

    Οι χώροι παίρνουν σχεδόν τετράγωνες αναλογίες (καλύτερη τήρηση ελάχιστης
    πλευράς). Οι εσωτερικές παρειές αφήνουν μισό πάχος τοίχου ti/2· οι πλευρές
    που πέφτουν στο εξωτερικό περίβλημα `interior`=(pix0,pix1,piy0,piy1)
    «κουμπώνουν» ακριβώς σε αυτό ώστε ο χώρος να εφάπτεται στον εξωτ. τοίχο.
    Επιστρέφει (rooms, ok) — ok=False αν κάποιος χώρος βγήκε κάτω από το min.
    """
    if not reqs:
        return [], True
    bw, bh = x1 - x0, y1 - y0
    if bw <= 0 or bh <= 0:
        return [], False
    pix0, pix1, piy0, piy1 = interior
    eps = 1e-4
    # ταξινόμηση κατά φθίνον εμβαδόν (ποιότητα squarify)· κατοπτρισμός ως προς X
    ordered = sorted(reqs, key=lambda r: -r.target_area)
    total = sum(r.target_area for r in ordered) or 1.0
    scaled = [r.target_area / total * (bw * bh) for r in ordered]
    rects: List[Tuple[float, float, float, float]] = []
    _squarify(scaled, x0, y0, bw, bh, rects)

    rooms: List[Room] = []
    ok = True
    for r, (rx, ry, rw, rh) in zip(ordered, rects):
        gx0, gx1, gy0, gy1 = rx, rx + rw, ry, ry + rh
        if mirror:
            gx0, gx1 = x0 + (x1 - (rx + rw)), x0 + (x1 - rx)
        # εσωτερική παρειά ti/2, εκτός αν η πλευρά πέφτει στο εξωτ. περίβλημα
        ax0 = pix0 if abs(gx0 - pix0) < eps else gx0 + ti / 2.0
        ax1 = pix1 if abs(gx1 - pix1) < eps else gx1 - ti / 2.0
        ay0 = piy0 if abs(gy0 - piy0) < eps else gy0 + ti / 2.0
        ay1 = piy1 if abs(gy1 - piy1) < eps else gy1 - ti / 2.0
        # Το «στενό περίγραμμα» αναφέρεται μόνο για χώρους κύριας χρήσης &
        # υπνοδωμάτια (οι ελάχ. διαστάσεις βοηθητικών §2.2 είναι πιο ελαστικές).
        significant = r.category.is_main_use or r.category in (
            Category.BEDROOM, Category.BEDROOM_MASTER)
        short = min(ax1 - ax0, ay1 - ay0)
        if significant and short < r.min_width - 0.10:
            ok = False
        rooms.append(Room(r.category, r.name, ax0, ay0, max(ax1, ax0 + 0.3),
                          max(ay1, ay0 + 0.3)))
    return rooms, ok


# ─────────────────────────────── Ανοίγματα ───────────────────────────────────

def _touch_sides(room: Room, plan: FloorPlan) -> List[str]:
    """Ποιες πλευρές του χώρου εφάπτονται στο εξωτερικό περίβλημα."""
    te = plan.ext_wall
    sides = []
    tol = 1e-6
    if abs(room.x0 - te) < 1e-3:
        sides.append("W")
    if abs(room.x1 - (plan.width_ew - te)) < 1e-3:
        sides.append("E")
    if abs(room.y0 - te) < 1e-3:
        sides.append("S")
    if abs(room.y1 - (plan.length_ns - te)) < 1e-3:
        sides.append("N")
    return sides


def _side_length(room: Room, side: str) -> float:
    return room.w if side in ("N", "S") else room.d


def _add_window(room: Room, side: str, ratio: float = 0.16) -> None:
    """Παράθυρο στη μέση της πλευράς, μήκους ~ratio·(εμβαδόν)/1,4 (ύψος υαλ.≈1,4 m)."""
    seglen = _side_length(room, side)
    # απαιτούμενο μήκος για επιφάνεια υαλοπίνακα ≥10% (ύψος υαλ. ~1,40 m)
    need = max(0.9, 0.10 * room.area / 1.40)
    width = min(max(need, 0.9), seglen - 0.6)
    if width <= 0.3:
        return
    offset = (seglen - width) / 2.0
    room.openings.append(Opening("window", side, offset, width, to_exterior=True))


def _add_door(room: Room, side: str, width: float = 0.90,
              exterior: bool = False) -> None:
    seglen = _side_length(room, side)
    w = min(width, seglen - 0.3)
    if w <= 0.2:
        return
    offset = (seglen - w) / 2.0
    room.openings.append(Opening("door", side, offset, w, to_exterior=exterior))


def _assign_openings(plan: FloorPlan, corridor: Optional[Room],
                     south_rooms: List[Room], north_rooms: List[Room]) -> None:
    """Τοποθετεί παράθυρα (εξωτερικά) και θύρες (προς διάδρομο/είσοδο)."""
    door_w = {Category.BATH: 0.80, Category.WC: 0.70, Category.STORAGE: 0.80,
              Category.WARDROBE: 0.80}
    # Παράθυρα σε χώρους κύριας χρήσης + κουζίνα + λουτρά/wc (αερισμός)
    for room in plan.rooms:
        if room.category in (Category.CORRIDOR, Category.STAIRS):
            continue
        sides = _touch_sides(room, plan)
        if not sides:
            continue
        needs_window = room.category.is_main_use or room.category in (
            Category.BATH, Category.WC)
        if not needs_window:
            continue
        # Προτίμηση: Νότος > Ανατολή > Βορράς > Δύση (βιοκλιματικά, §5.3)
        pref = {"S": 0, "E": 1, "N": 2, "W": 3}
        side = sorted(sides, key=lambda s: pref[s])[0]
        _add_window(room, side, )

    # Θύρες προς τον διάδρομο
    if corridor is not None:
        for room in south_rooms:
            _add_door(room, "N", door_w.get(room.category, 0.90))  # προς βορρά (διάδρ.)
        for room in north_rooms:
            _add_door(room, "S", door_w.get(room.category, 0.90))  # προς νότο (διάδρ.)
    else:
        # χωρίς διάδρομο: οι χώροι ανοίγουν προς τον γειτονικό χώρο υποδοχής
        for room in plan.rooms:
            if room.category in (Category.HALL, Category.CORRIDOR):
                continue
            _add_door(room, "N", door_w.get(room.category, 0.90))

    # Θύρα εισόδου: ΠΑΝΤΑ στην εξωτ. όψη του ζητούμενου προσανατολισμού, στον
    # καταλληλότερο χώρο που εφάπτεται σε αυτήν (προτίμηση: Είσοδος/Χωλ >
    # καθιστικό > σαλόνι > διάδρομος > οποιοσδήποτε).
    ent = plan.entrance.value if plan.entrance else "N"
    pref_order = {
        Category.HALL: 0, Category.LIVING: 1, Category.SALON: 2,
        Category.CORRIDOR: 3, Category.KITCHEN: 4,
    }
    W, L = plan.width_ew, plan.length_ns
    cand = [r for r in plan.rooms
            if ent in _touch_sides(r, plan) and r.category != Category.STAIRS]

    def _centrality(r: Room) -> float:
        return abs(r.cx - W / 2) if ent in ("N", "S") else abs(r.cy - L / 2)

    if cand:
        cand.sort(key=lambda r: (pref_order.get(r.category, 9), _centrality(r)))
        _add_door(cand[0], ent, 1.00, exterior=True)
    else:
        # κανένας χώρος δεν φτάνει στην όψη· βάλε την είσοδο στον διάδρομο/hall
        target = next((r for r in plan.rooms if r.category in (
            Category.HALL, Category.CORRIDOR, Category.LIVING)), None)
        if target is not None:
            sides = _touch_sides(target, plan)
            _add_door(target, sides[0] if sides else ent, 1.00, exterior=True)


# ─────────────────────────── Διάταξη ενός ορόφου ──────────────────────────────

def layout_floor(width_ew: float, length_ns: float, spec: BuildingSpec,
                 program: List[RoomReq], floor_label: str, seed: int,
                 entrance: Orientation, variant: int = 0) -> Tuple[FloorPlan, List[str]]:
    """Δημιουργεί μία κάτοψη ορόφου με ζωνική διάταξη.

    Το `variant` διαφοροποιεί δομικά την κάθε πρόταση (κατοπτρισμός Α–Δ, λόγος
    βάθους ζωνών, πλάτος διαδρόμου) ώστε οι λύσεις να είναι εμφανώς διαφορετικές.
    """
    rng = random.Random(seed)
    warnings: List[str] = []
    te, ti = spec.ext_wall, spec.int_wall

    plan = FloorPlan(floor_label, width_ew, length_ns, te, ti, entrance=entrance)

    ix0, ix1 = te, width_ew - te
    iy0, iy1 = te, length_ns - te
    iw, ih = ix1 - ix0, iy1 - iy0
    if iw <= 0.5 or ih <= 0.5:
        warnings.append("Το περίγραμμα είναι πολύ μικρό για το πάχος τοιχοποιίας.")
        return plan, warnings

    # Διαχωρισμός σε ζώνες: ημέρα (νότια, κάτω) / νύχτα-βοηθητικά (βόρεια, πάνω)
    south = [r for r in program if r.category in SOUTH_CATEGORIES]
    north = [r for r in program if r.category not in SOUTH_CATEGORIES]

    # Ο χώρος υποδοχής (χωλ) παραμένει στη ζώνη βοηθητικών/νύχτας (κοντά στο
    # κλιμακοστάσιο). Η ΘΥΡΑ εισόδου τοποθετείται πάντα στην εξωτ. όψη του
    # ζητούμενου προσανατολισμού (βλ. _assign_openings), οπότε για είσοδο από Νότο
    # η πρόσβαση γίνεται απευθείας στον κεντρικό χώρο ημέρας της νότιας όψης.

    has_corridor = bool(south) and bool(north)
    interior = (ix0, ix1, iy0, iy1)

    # Ελάχιστα βάθη ζωνών
    def min_depth(reqs: List[RoomReq]) -> float:
        if not reqs:
            return 0.0
        has_bed = any(r.category in (Category.BEDROOM, Category.BEDROOM_MASTER)
                      for r in reqs)
        base = spec.min_bedroom_side if has_bed else MIN_ROOM_DEPTH
        if any(r.category in (Category.LIVING, Category.SALON) for r in reqs):
            base = max(base, 3.20)
        return base

    minS, minN = min_depth(south), min_depth(north)

    def _boost(reqs: List[RoomReq], factor: float) -> List[RoomReq]:
        return [dc_replace(r, target_area=r.target_area * factor)
                if r.category in (Category.BEDROOM, Category.BEDROOM_MASTER)
                else r for r in reqs]

    def attempt(corridor_d: float, frac: float, bed_boost: float,
                mirror: bool) -> dict:
        usable = ih - corridor_d
        if south and north:
            dS = usable * frac
            dN = usable - dS
            if dS < minS:
                dS, dN = minS, usable - minS
            if dN < minN:
                dN, dS = minN, usable - minN
            dS = max(dS, 0.1)
            dN = max(usable - dS, 0.1)
        elif south:
            dS, dN, corridor_d = ih, 0.0, 0.0
        else:
            dS, dN, corridor_d = 0.0, ih, 0.0

        s_rooms = n_rooms = []
        rms: List[Room] = []
        if south:
            s_rooms, _ = _place_band(_boost(south, bed_boost), ix0, ix1, iy0,
                                     iy0 + dS, ti, mirror, interior)
            rms += s_rooms
        if north:
            n_rooms, _ = _place_band(_boost(north, bed_boost), ix0, ix1,
                                     iy1 - dN, iy1, ti, mirror, interior)
            rms += n_rooms
        corr: Optional[Room] = None
        if has_corridor and corridor_d > 0.05:
            cy0, cy1 = iy0 + dS, iy1 - dN
            if cy1 - cy0 > 0.05:
                corr = Room(Category.CORRIDOR, "Διάδρομος", ix0, cy0, ix1, cy1)
                rms.append(corr)
        # βαθμολογία: παραβιάσεις ελάχ. πλευράς + ποιότητα αναλογιών
        viol = 0
        quality = 0.0
        for r in rms:
            if r.category in (Category.BEDROOM, Category.BEDROOM_MASTER):
                if min(r.w, r.d) < spec.min_bedroom_side - 0.05:
                    viol += 1
            elif r.category.is_main_use:
                if min(r.w, r.d) < 2.6:
                    viol += 1
            if r.category != Category.CORRIDOR and r.d > 0 and r.w > 0:
                quality += max(r.w / r.d, r.d / r.w)
        return {"rooms": rms, "south": s_rooms, "north": n_rooms, "corr": corr,
                "viol": viol, "quality": quality}

    base_frac = (sum(r.target_area for r in south)
                 / (sum(r.target_area for r in south)
                    + sum(r.target_area for r in north))) if (south and north) else 0.5

    # Δομική διαφοροποίηση ανά πρόταση (variant)
    force_mirror = bool(variant % 2)
    frac_bias = (0.0, 0.06, -0.06)[variant % 3]
    corr_opts = ((1.00, 1.10, 1.20), (1.20, 1.10), (1.10, 1.00))[variant % 3]

    cands: List[dict] = []
    for cd in corr_opts:
        for boost in (1.0, 1.3, 1.7, 2.1):
            for df in (-0.05, 0.0, 0.05):
                fr = min(0.68, max(0.34, base_frac + frac_bias + df))
                cands.append(attempt(cd, fr, boost, force_mirror))

    best_score = min((c["viol"], round(c["quality"], 2)) for c in cands)
    best = [c for c in cands if (c["viol"], round(c["quality"], 2)) == best_score]
    chosen = best[seed % len(best)]

    plan.rooms = chosen["rooms"]
    _assign_openings(plan, chosen["corr"], chosen["south"], chosen["north"])

    # Τελικές παρατηρήσεις ανά χώρο (ελάχ. πλευρά 3,00×3,00 του αιτήματος)
    for r in plan.rooms:
        if r.category in (Category.BEDROOM, Category.BEDROOM_MASTER):
            if min(r.w, r.d) < spec.min_bedroom_side - 0.05:
                warnings.append(
                    f"{r.name}: {r.w:.2f}×{r.d:.2f} m — ελάχιστη πλευρά κάτω από "
                    f"{spec.min_bedroom_side:.2f} m (στενό περίγραμμα).")
    return plan, warnings


# ─────────────────────────── Διαστασιολόγηση περιγράμματος ────────────────────

def _size_footprint(spec: BuildingSpec, program_floors: List[List[RoomReq]],
                    seed: int) -> Tuple[float, float]:
    """Υπολογίζει εξωτερικές διαστάσεις (W_ew, L_ns) εντός ορίων & max εμβαδού."""
    rng = random.Random(seed * 7 + 11)
    # καθαρό εμβαδόν του πιο απαιτητικού ορόφου
    net = max(sum(r.target_area for r in fl) for fl in program_floors)
    circ = net * CIRC_FRACTION
    gross_needed = (net + circ) * (1.0 + WALL_FRACTION)

    wmax, lmax = spec.max_width_ew, spec.max_length_ns
    env = wmax * lmax
    eff_max = min(spec.max_total_area, env)

    target = min(eff_max, gross_needed)
    if target < 0.6 * eff_max:
        # μικρή προσαύξηση για ποικιλία, χωρίς υπέρβαση ορίων
        target = min(eff_max, target * (1.0 + 0.10 * rng.random()))

    # κλιμάκωση του περιγράμματος διατηρώντας τον λόγο πλευρών του ορίου
    scale = math.sqrt(target / env) if env > 0 else 1.0
    scale = min(1.0, scale)
    w = wmax * scale
    l = lmax * scale
    # μικρή μεταβολή αναλογίας (±6%) εντός ορίων, για διαφορετικές λύσεις
    a = 1.0 + (rng.random() - 0.5) * 0.12
    w = min(wmax, w * a)
    l = min(lmax, l / a)
    return round(w, 2), round(l, 2)


# ─────────────────────────────── Παραγωγή προτάσεων ───────────────────────────

def generate_proposals(spec: BuildingSpec) -> List[Proposal]:
    errs = spec.validate()
    if errs:
        raise ValueError("Σφάλματα δεδομένων:\n- " + "\n- ".join(errs))

    program_floors = build_program(spec)
    floor_labels = (["Ισόγειο"] if spec.floors == 1
                    else ["Ισόγειο", "Α' Όροφος"])

    proposals: List[Proposal] = []
    for i in range(spec.num_proposals):
        seed = 1000 + i * 37
        w, l = _size_footprint(spec, program_floors, seed)
        prop = Proposal(index=i + 1, spec=spec, seed=seed)
        for fl_idx, program in enumerate(program_floors):
            plan, warns = layout_floor(
                w, l, spec, program, floor_labels[fl_idx], seed + fl_idx,
                spec.entrance, variant=i)
            prop.floors.append(plan)
            for wn in warns:
                tag = f"[{floor_labels[fl_idx]}] {wn}"
                if tag not in prop.warnings:
                    prop.warnings.append(tag)
        proposals.append(prop)
    return proposals


# ─────────────────────── Μικτές (εξωτερικές) διαστάσεις χώρου ──────────────────

def room_gross_dims(room: Room, plan: FloorPlan) -> Tuple[float, float]:
    """Μικτές διαστάσεις χώρου (καθαρές + μισό εσωτ. τοίχου ή πλήρης εξωτ.).

    Επιστρέφει (μικτό_πλάτος, μικτό_βάθος) — άξονες Α–Δ και Β–Ν αντίστοιχα.
    """
    te, ti = plan.ext_wall, plan.int_wall
    sides = set(_touch_sides(room, plan))
    left = te if "W" in sides else ti / 2.0
    right = te if "E" in sides else ti / 2.0
    bottom = te if "S" in sides else ti / 2.0
    top = te if "N" in sides else ti / 2.0
    return room.w + left + right, room.d + bottom + top

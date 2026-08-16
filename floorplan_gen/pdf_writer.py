"""Έξοδος PDF (ReportLab) — κάτοψη σε κλίμακα με διαστάσεις, βέλος βορρά,
γραμμική κλίμακα, υπόμνημα και πίνακες χώρων/ελέγχου φωτισμού-αερισμού.

Ο Βορράς είναι πάντα στο επάνω μέρος του σχεδίου. Κάθε πρόταση δίνει:
  * μία σελίδα σχεδίου ανά όροφο (σε τυποποιημένη κλίμακα 1:50/1:100/…),
  * μία σελίδα με πίνακα χώρων (καθαρές & μικτές διαστάσεις) και έλεγχο Κ.Κ.
"""
from __future__ import annotations

import datetime
import os
from typing import List, Tuple

from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .compliance import check_floor, floor_summary, ComplianceRow
from .layout import _touch_sides, room_gross_dims
from .models import Category, FloorPlan, Proposal, Room
from .textutil import fmt

PAGE = landscape(A3)                      # 420 × 297 mm
PT_PER_M = 72.0 / 25.4 * 1000.0           # σημεία ανά μέτρο σε κλίμακα 1:1
SCALES = [20, 25, 50, 75, 100, 150, 200, 250, 300]

FONT = "DejaVu"
FONT_B = "DejaVu-Bold"

WALL_GRAY = 0.45
_ROOM_FILL = {
    Category.LIVING: (0.90, 0.95, 1.00),
    Category.SALON: (0.90, 0.93, 1.00),
    Category.KITCHEN: (1.00, 0.96, 0.86),
    Category.BEDROOM_MASTER: (0.91, 1.00, 0.91),
    Category.BEDROOM: (0.94, 1.00, 0.94),
    Category.BATH: (0.88, 0.97, 0.98),
    Category.WC: (0.88, 0.97, 0.98),
    Category.STORAGE: (0.95, 0.95, 0.95),
    Category.WARDROBE: (0.95, 0.95, 0.95),
    Category.HALL: (0.97, 0.94, 0.98),
    Category.CORRIDOR: (0.98, 0.98, 0.98),
    Category.STAIRS: (0.93, 0.93, 0.90),
}


def register_fonts() -> None:
    if FONT in pdfmetrics.getRegisteredFontNames():
        return
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        (os.path.join(here, "assets", "DejaVuSans.ttf"),
         os.path.join(here, "assets", "DejaVuSans-Bold.ttf")),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for reg, bold in candidates:
        if os.path.exists(reg) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont(FONT, reg))
            pdfmetrics.registerFont(TTFont(FONT_B, bold))
            return
    # έσχατη λύση: ενσωματωμένη Vera (χωρίς ελληνικά — αποφεύγει κατάρρευση)
    pdfmetrics.registerFont(TTFont(FONT, os.path.join(
        os.path.dirname(__import__("reportlab").__file__), "fonts", "Vera.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_B, os.path.join(
        os.path.dirname(__import__("reportlab").__file__), "fonts", "VeraBd.ttf")))


# ─────────────────────────── επιλογή κλίμακας ─────────────────────────────────

def choose_scale(w_m: float, l_m: float, avail_w_mm: float,
                 avail_h_mm: float) -> int:
    for d in SCALES:
        if w_m * 1000.0 / d <= avail_w_mm and l_m * 1000.0 / d <= avail_h_mm:
            return d
    return SCALES[-1]


def _wall_thickness_side(room: Room, plan: FloorPlan, side: str) -> float:
    return plan.ext_wall if side in _touch_sides(room, plan) else plan.int_wall


# ─────────────────────────── σχεδίαση ορόφου ──────────────────────────────────

def _draw_floor_page(c: canvas.Canvas, plan: FloorPlan, prop: Proposal) -> None:
    W, L, te = plan.width_ew, plan.length_ns, plan.ext_wall
    margin = 20 * mm
    title_h = 32 * mm
    avail_w_mm = (PAGE[0] - 2 * margin) / mm - 10
    avail_h_mm = (PAGE[1] - 2 * margin - title_h) / mm - 10
    denom = choose_scale(W, L, avail_w_mm, avail_h_mm)
    k = PT_PER_M / denom                              # σημεία ανά μέτρο

    draw_w = W * k
    draw_h = L * k
    ox = margin + ((PAGE[0] - 2 * margin) - draw_w) / 2.0
    oy = margin + title_h + ((PAGE[1] - 2 * margin - title_h) - draw_h) / 2.0

    def mx(x: float) -> float: return ox + x * k
    def my(y: float) -> float: return oy + y * k

    # 1) τοίχοι = γεμάτη μάζα περιγράμματος (ανά κύτταρο → σωστό Γ-σχήμα)
    c.setFillGray(WALL_GRAY)
    for (cx0, cy0, cx1, cy1) in (plan.cells or [(0, 0, W, L)]):
        c.rect(mx(cx0), my(cy0), (cx1 - cx0) * k, (cy1 - cy0) * k, stroke=0, fill=1)

    # 2) χώροι
    c.setLineWidth(0.5)
    for room in plan.rooms:
        rgb = _ROOM_FILL.get(room.category, (1, 1, 1))
        c.setFillColorRGB(*rgb)
        c.setStrokeGray(0.15)
        c.rect(mx(room.x0), my(room.y0), room.w * k, room.d * k, stroke=1, fill=1)

    # Σημ.: οι εξωτερικοί τοίχοι εμφανίζονται αυτόματα με πάχος te, καθώς κάθε
    # χώρος τοποθετείται εσωτερικά κατά te στις εξωτερικές πλευρές (βλ. layout),
    # ενώ το τμήμα εξωτερικού τοίχου που βρίσκεται εσωτερικά του περιγράμματος
    # (π.χ. σε εσοχή Γ/Τ) σημειώνεται ως εσωτερικό → πάχος ti (βλ. _place_row).
    outline = plan.outline or [(0, 0), (W, 0), (W, L), (0, L)]

    # 2β) εξωτερικό περίγραμμα (πολύγωνο) — έντονη γραμμή
    c.setStrokeGray(0.0)
    c.setLineWidth(1.4)
    p = c.beginPath()
    p.moveTo(mx(outline[0][0]), my(outline[0][1]))
    for (x, y) in outline[1:]:
        p.lineTo(mx(x), my(y))
    p.close()
    c.drawPath(p, stroke=1, fill=0)

    # 3) ανοίγματα (λευκά κενά στους τοίχους + σύμβολο)
    for room in plan.rooms:
        _draw_openings(c, room, plan, mx, my, k)

    # 4) ετικέτες χώρων
    for room in plan.rooms:
        _label_room(c, room, plan, mx, my, k)

    # 5) διαστάσεις (συνολικές εξωτερικές + αλυσίδα πλατών κάτω)
    _draw_dims(c, plan, mx, my, k)

    # 6) βέλος βορρά, γραμμική κλίμακα, υπόμνημα, στοιχεία
    _draw_north(c, mx(W) + 8 * mm, my(L) - 2 * mm)
    _draw_scalebar(c, ox, margin + title_h - 6 * mm, denom)
    _draw_titleblock(c, plan, prop, denom, margin)


def _draw_openings(c, room: Room, plan: FloorPlan, mx, my, k) -> None:
    for op in room.openings:
        t = _wall_thickness_side(room, plan, op.side)
        c.setFillGray(1.0)
        c.setStrokeGray(1.0)
        if op.side in ("N", "S"):
            x = room.x0 + op.offset
            y = room.y1 if op.side == "N" else room.y0
            yy = y if op.side == "N" else y - t
            c.rect(mx(x), my(yy), op.width * k, t * k, stroke=0, fill=1)
        else:
            y = room.y0 + op.offset
            x = room.x1 if op.side == "E" else room.x0
            xx = x if op.side == "E" else x - t
            c.rect(mx(xx), my(y), t * k, op.width * k, stroke=0, fill=1)
        # σύμβολο
        if op.kind == "opening":
            # ανοιχτό πέρασμα (λειτουργική επικοινωνία): μόνο το λευκό κενό
            continue
        c.setStrokeColorRGB(0.10, 0.35, 0.75)
        c.setLineWidth(0.7)
        (ax, ay), (bx, by) = _endpoints(room, op)
        if op.kind == "window":
            c.line(mx(ax), my(ay), mx(bx), my(by))
        else:
            # φύλλο θύρας + τόξο
            c.setStrokeColorRGB(0.70, 0.20, 0.20)
            if op.side in ("N", "S"):
                sgn = -1 if op.side == "N" else 1
                c.line(mx(ax), my(ay), mx(ax), my(ay + sgn * op.width))
                c.arc(mx(ax - op.width), my(ay - op.width), mx(ax + op.width),
                      my(ay + op.width), 0, 90 if sgn > 0 else -90)
            else:
                sgn = 1 if op.side == "W" else -1
                c.line(mx(ax), my(ay), mx(ax + sgn * op.width), my(ay))


def _endpoints(room: Room, op) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    if op.side == "S":
        return (room.x0 + op.offset, room.y0), (room.x0 + op.offset + op.width, room.y0)
    if op.side == "N":
        return (room.x0 + op.offset, room.y1), (room.x0 + op.offset + op.width, room.y1)
    if op.side == "W":
        return (room.x0, room.y0 + op.offset), (room.x0, room.y0 + op.offset + op.width)
    return (room.x1, room.y0 + op.offset), (room.x1, room.y0 + op.offset + op.width)


def _label_room(c, room: Room, plan: FloorPlan, mx, my, k) -> None:
    if not room.name:                       # τμήμα συνέχειας (π.χ. προέκταση διαδρ.)
        return
    if room.category == Category.CORRIDOR and room.area < 1.5:
        return
    cx, cy = mx(room.cx), my(room.cy)
    gw, gd = room_gross_dims(room, plan)
    box_w = room.w * k
    fs = max(4.5, min(8.0, box_w / (max(6, len(room.name)) * 0.62)))
    c.setFillGray(0.0)
    c.setFont(FONT_B, fs)
    c.drawCentredString(cx, cy + fs * 0.9, room.name)
    c.setFont(FONT, fs * 0.82)
    c.drawCentredString(cx, cy - fs * 0.2, f"{fmt(room.area)} m²")
    if room.d * k > 34:
        c.setFont(FONT, fs * 0.75)
        c.setFillGray(0.25)
        c.drawCentredString(cx, cy - fs * 1.25, f"εσ. {fmt(room.w)}×{fmt(room.d)}")
        if room.d * k > 46:
            c.drawCentredString(cx, cy - fs * 2.1, f"μικτ. {fmt(gw)}×{fmt(gd)}")


def _draw_dims(c, plan: FloorPlan, mx, my, k) -> None:
    W, L = plan.width_ew, plan.length_ns
    c.setStrokeGray(0.0)
    c.setFillGray(0.0)
    c.setLineWidth(0.4)
    # συνολικό πλάτος (κάτω)
    yb = my(0) - 10 * mm
    c.line(mx(0), yb, mx(W), yb)
    for xx in (0, W):
        c.line(mx(xx), yb - 1.5 * mm, mx(xx), yb + 1.5 * mm)
    c.setFont(FONT, 8)
    c.drawCentredString(mx(W / 2), yb - 4.5 * mm, f"{fmt(W)} m (Ανατ.–Δύση)")
    # συνολικό μήκος (αριστερά)
    xl = mx(0) - 10 * mm
    c.line(xl, my(0), xl, my(L))
    for yy in (0, L):
        c.line(xl - 1.5 * mm, my(yy), xl + 1.5 * mm, my(yy))
    c.saveState()
    c.translate(xl - 4.5 * mm, my(L / 2))
    c.rotate(90)
    c.drawCentredString(0, 0, f"{fmt(L)} m (Βορ.–Νότος)")
    c.restoreState()


def _draw_north(c, x: float, y: float) -> None:
    c.setFillGray(0.0)
    c.setStrokeGray(0.0)
    p = c.beginPath()
    p.moveTo(x, y)
    p.lineTo(x - 4 * mm, y - 11 * mm)
    p.lineTo(x, y - 7 * mm)
    p.lineTo(x + 4 * mm, y - 11 * mm)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    c.setFont(FONT_B, 11)
    c.drawCentredString(x, y + 3 * mm, "Β")


def _draw_scalebar(c, x: float, y: float, denom: int) -> None:
    k = PT_PER_M / denom
    c.setFont(FONT, 7)
    c.setFillGray(0.0)
    c.setStrokeGray(0.0)
    c.drawString(x, y + 4 * mm, f"Κλίμακα 1:{denom}")
    seg = 1.0  # 1 m ανά τμήμα, 5 τμήματα
    for i in range(5):
        c.setFillGray(0.0 if i % 2 == 0 else 1.0)
        c.rect(x + i * seg * k, y, seg * k, 1.6 * mm, stroke=1, fill=1)
    c.setFillGray(0.0)
    for i in range(6):
        c.drawCentredString(x + i * seg * k, y - 3 * mm, str(i))
    c.drawString(x + 5 * seg * k + 2 * mm, y - 3 * mm, "m")


def _draw_titleblock(c, plan: FloorPlan, prop: Proposal, denom: int,
                     margin: float) -> None:
    w, h = 108 * mm, 26 * mm
    x0 = PAGE[0] - margin - w
    y0 = margin
    c.setStrokeGray(0.0)
    c.setLineWidth(0.8)
    c.rect(x0, y0, w, h, stroke=1, fill=0)
    c.setFont(FONT_B, 8)
    c.setFillGray(0.0)
    c.drawString(x0 + 3 * mm, y0 + h - 6 * mm,
                 "Τεχνικό Γραφείο Μελετών — Γεωργακόπουλος Χρ. / Φουντάς Αθ.")
    c.setFont(FONT, 7.5)
    today = datetime.date.today().strftime("%d.%m.%Y")
    lines = [
        f"Έργο: {prop.spec.project_name}",
        f"{prop.title} — {plan.floor_label}",
        f"Κλίμακα 1:{denom}   ·   Μικτό εμβ.: {fmt(plan.footprint_area)} m²",
        f"Είσοδος: {prop.spec.entrance.gr}   ·   {prop.spec.location}",
        f"Ημερομηνία: {today}   ·   Σχεδ.: Γεωργακόπουλος Χρ. (ΑΜ ΤΕΕ 101893)",
    ]
    for i, ln in enumerate(lines):
        c.drawString(x0 + 3 * mm, y0 + h - 11 * mm - i * 3.6 * mm, ln)


# ─────────────────────────── σελίδα πινάκων ───────────────────────────────────

def _draw_table(c, x: float, y: float, headers: List[str], widths: List[float],
                rows: List[List[str]], fs: float = 7.5,
                rowh: float = 5.2 * mm) -> float:
    total_w = sum(widths)
    c.setFont(FONT_B, fs)
    c.setFillGray(0.85)
    c.rect(x, y - rowh, total_w, rowh, stroke=0, fill=1)
    c.setFillGray(0.0)
    c.setStrokeGray(0.4)
    c.setLineWidth(0.3)
    cx = x
    for htxt, wd in zip(headers, widths):
        c.drawString(cx + 1.2 * mm, y - rowh + 1.6 * mm, htxt)
        cx += wd
    yy = y - rowh
    c.setFont(FONT, fs)
    for r in rows:
        cx = x
        yy -= rowh
        for cell, wd in zip(r, widths):
            c.drawString(cx + 1.2 * mm, yy + 1.6 * mm, str(cell))
            cx += wd
        c.line(x, yy, x + total_w, yy)
    # πλαίσιο + κατακόρυφες
    c.rect(x, yy, total_w, y - yy, stroke=1, fill=0)
    cx = x
    for wd in widths[:-1]:
        cx += wd
        c.line(cx, yy, cx, y)
    return yy


def _draw_summary_page(c: canvas.Canvas, prop: Proposal) -> None:
    margin = 18 * mm
    x = margin
    y = PAGE[1] - margin
    c.setFont(FONT_B, 13)
    c.setFillGray(0.0)
    c.drawString(x, y, f"{prop.spec.project_name} — {prop.title}: Πίνακες χώρων & έλεγχοι")
    y -= 6 * mm
    c.setFont(FONT, 8.5)
    c.drawString(x, y, "Διαστάσεις: «καθαρές» = εσωτερικές ελεύθερες · «μικτές» = "
                       "με τοίχους (εξωτ. πλήρες πάχος, εσωτ. μισό). Βορράς: επάνω.")
    y -= 8 * mm

    for plan in prop.floors:
        c.setFont(FONT_B, 10)
        c.drawString(x, y, f"■ {plan.floor_label}  (μικτό {fmt(plan.footprint_area)} m², "
                           f"καθαρό {fmt(plan.net_area)} m²)")
        y -= 5 * mm
        # Πίνακας χώρων
        headers = ["#", "Χώρος", "Καθ. εμβ. (m²)", "Καθ. Α×Β (m)",
                   "Μικτές Α×Β (m)", "Ζώνη"]
        widths = [8 * mm, 45 * mm, 26 * mm, 30 * mm, 32 * mm, 22 * mm]
        rows = []
        for i, room in enumerate(plan.rooms, 1):
            gw, gd = room_gross_dims(room, plan)
            zone = "κύρια" if room.category.is_main_use else "βοηθ."
            rows.append([i, room.name, fmt(room.area),
                         f"{fmt(room.w)}×{fmt(room.d)}",
                         f"{fmt(gw)}×{fmt(gd)}", zone])
        y = _draw_table(c, x, y, headers, widths, rows)
        y -= 6 * mm

        # Πίνακας ελέγχου φωτισμού/αερισμού
        c.setFont(FONT_B, 9)
        c.drawString(x, y, "Έλεγχος φωτισμού & αερισμού (Κ.Κ. αρ. 20 §5.1.2 / αρ. 21 §5.2)")
        y -= 4.5 * mm
        crows: List[ComplianceRow] = check_floor(plan)
        headers2 = ["Χώρος", "Εμβ.", "Φως≥10%", "Υαλοπ.", "Αερ.≥5%",
                    "Ανοιγ.", "Φως", "Αερ."]
        widths2 = [40 * mm, 16 * mm, 20 * mm, 18 * mm, 20 * mm, 18 * mm,
                   12 * mm, 12 * mm]
        rows2 = []
        for r in crows:
            rows2.append([
                r.name, fmt(r.net_area, 1),
                fmt(r.req_light, 2), fmt(r.window_area, 2),
                fmt(r.req_vent, 2), fmt(r.window_area * 0.5, 2),
                "✓" if r.light_ok else "✗",
                "✓" if r.vent_ok else "✗",
            ])
        y = _draw_table(c, x, y, headers2, widths2, rows2, fs=7)
        y -= 4 * mm
        c.setFont(FONT, 8)
        c.drawString(x, y, "→ " + floor_summary(crows))
        y -= 9 * mm
        if y < 60 * mm:
            c.showPage()
            y = PAGE[1] - margin

    # Προειδοποιήσεις
    if prop.warnings:
        c.setFont(FONT_B, 9.5)
        c.setFillColorRGB(0.6, 0.1, 0.1)
        c.drawString(x, y, "Παρατηρήσεις / περιορισμοί:")
        y -= 4.5 * mm
        c.setFont(FONT, 8)
        c.setFillGray(0.0)
        for wn in prop.warnings:
            c.drawString(x + 3 * mm, y, "• " + wn)
            y -= 4 * mm
        y -= 3 * mm

    # Υποσημείωση νομικού πλαισίου
    c.setFont(FONT, 7)
    c.setFillGray(0.35)
    c.drawString(x, margin,
                 "Σχηματικές προτάσεις προμελέτης βάσει instructions.md. Οι ελάχ. "
                 "διαστάσεις χώρων (§2.2/Παράρτημα Α) είναι ΜΗ δεσμευτικές· δεσμευτικοί "
                 "μόνο οι έλεγχοι ύψους/φωτισμού/αερισμού. Απαιτείται έλεγχος ΣΔ/κάλυψης "
                 "/ύψους/Δ-δ πριν την αδειοδότηση.")


# ─────────────────────────────── Δημόσιο API ─────────────────────────────────

def write_proposal_pdf(prop: Proposal, path: str) -> None:
    register_fonts()
    c = canvas.Canvas(path, pagesize=PAGE)
    c.setTitle(f"{prop.spec.project_name} — {prop.title}")
    c.setAuthor("Τεχνικό Γραφείο Μελετών — Γεωργακόπουλος Χρ. / Φουντάς Αθ.")
    for plan in prop.floors:
        _draw_floor_page(c, plan, prop)
        c.showPage()
    _draw_summary_page(c, prop)
    c.showPage()
    c.save()


def write_all_pdf(proposals: List[Proposal], path: str) -> None:
    """Ένα ενιαίο PDF με όλες τις προτάσεις."""
    register_fonts()
    c = canvas.Canvas(path, pagesize=PAGE)
    if proposals:
        c.setTitle(f"{proposals[0].spec.project_name} — Προτάσεις κατόψεων")
        c.setAuthor("Τεχνικό Γραφείο Μελετών — Γεωργακόπουλος Χρ. / Φουντάς Αθ.")
    for prop in proposals:
        for plan in prop.floors:
            _draw_floor_page(c, plan, prop)
            c.showPage()
        _draw_summary_page(c, prop)
        c.showPage()
    c.save()

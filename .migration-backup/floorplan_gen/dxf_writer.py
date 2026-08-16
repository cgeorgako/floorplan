"""Έξοδος DXF R12 (AC1009) — χειρόγραφη, για μέγιστη συμβατότητα CAD.

Ακολουθείται το πρότυπο του γραφείου: μορφή AC1009/R12, γεωμετρία με ακολουθία
POLYLINE/VERTEX/SEQEND (όχι LWPOLYLINE), οργανωμένα layers. Οι συντεταγμένες
είναι σε μέτρα, κανόνας 1:1 (X→X, Y→Y), με τον Βορρά στο +Y.

Το ελληνικό κείμενο κωδικοποιείται σε ANSI_1253 ($DWGCODEPAGE) — ο κλασικός
τρόπος εμφάνισης ελληνικών σε DXF R12.
"""
from __future__ import annotations

from typing import List, Tuple

from .layout import room_gross_dims
from .models import Category, FloorPlan, Proposal, Room
from .textutil import fmt

# Χρώματα ACI ανά layer
LAYERS = [
    ("OUTLINE", 7),     # εξωτερικό περίγραμμα
    ("WALLS", 8),       # τοίχοι
    ("ROOMS", 3),       # όρια χώρων (καθαρά)
    ("OPENINGS", 1),    # ανοίγματα (θύρες/παράθυρα)
    ("TEXT", 7),        # ονόματα/εμβαδά
    ("DIMS", 4),        # διαστάσεις
    ("NORTH", 2),       # βέλος βορρά
    ("TITLE", 5),       # υπόμνημα/τίτλος
]


class DXF:
    """Απλός κατασκευαστής οντοτήτων DXF R12."""

    def __init__(self) -> None:
        self.ents: List[str] = []

    def line(self, layer: str, x1: float, y1: float, x2: float, y2: float) -> None:
        self.ents += ["0", "LINE", "8", layer,
                      "10", f"{x1:.4f}", "20", f"{y1:.4f}", "30", "0.0",
                      "11", f"{x2:.4f}", "21", f"{y2:.4f}", "31", "0.0"]

    def polyline(self, layer: str, pts: List[Tuple[float, float]],
                 closed: bool = True) -> None:
        self.ents += ["0", "POLYLINE", "8", layer, "66", "1",
                      "70", "1" if closed else "0",
                      "10", "0.0", "20", "0.0", "30", "0.0"]
        for (x, y) in pts:
            self.ents += ["0", "VERTEX", "8", layer,
                          "10", f"{x:.4f}", "20", f"{y:.4f}", "30", "0.0"]
        self.ents += ["0", "SEQEND", "8", layer]

    def rect(self, layer: str, x0: float, y0: float, x1: float, y1: float) -> None:
        self.polyline(layer, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True)

    def arc(self, layer: str, cx: float, cy: float, r: float,
            a0: float, a1: float) -> None:
        self.ents += ["0", "ARC", "8", layer,
                      "10", f"{cx:.4f}", "20", f"{cy:.4f}", "30", "0.0",
                      "40", f"{r:.4f}", "50", f"{a0:.2f}", "51", f"{a1:.2f}"]

    def text(self, layer: str, x: float, y: float, h: float, s: str,
             rot: float = 0.0, halign: int = 1, valign: int = 2) -> None:
        # halign 1=center, valign 2=middle → κείμενο κεντραρισμένο στο (x,y)
        self.ents += ["0", "TEXT", "8", layer,
                      "10", f"{x:.4f}", "20", f"{y:.4f}", "30", "0.0",
                      "40", f"{h:.4f}", "1", s, "50", f"{rot:.2f}",
                      "72", str(halign), "73", str(valign),
                      "11", f"{x:.4f}", "21", f"{y:.4f}", "31", "0.0"]

    def render(self) -> str:
        head = [
            "0", "SECTION", "2", "HEADER",
            "9", "$ACADVER", "1", "AC1009",
            "9", "$DWGCODEPAGE", "3", "ANSI_1253",
            "9", "$INSUNITS", "70", "6",   # 6 = meters
            "0", "ENDSEC",
        ]
        tables = ["0", "SECTION", "2", "TABLES",
                  "0", "TABLE", "2", "LAYER", "70", str(len(LAYERS))]
        for name, color in LAYERS:
            tables += ["0", "LAYER", "2", name, "70", "0",
                       "62", str(color), "6", "CONTINUOUS"]
        tables += ["0", "ENDTAB", "0", "ENDSEC"]
        body = ["0", "SECTION", "2", "ENTITIES"] + self.ents + ["0", "ENDSEC"]
        tail = ["0", "EOF"]
        return "\n".join(head + tables + body + tail) + "\n"


# ─────────────────────────── Σχεδίαση ανοιγμάτων ──────────────────────────────

def _opening_endpoints(room: Room, op) -> Tuple[Tuple[float, float],
                                                Tuple[float, float]]:
    if op.side == "S":
        y = room.y0
        return (room.x0 + op.offset, y), (room.x0 + op.offset + op.width, y)
    if op.side == "N":
        y = room.y1
        return (room.x0 + op.offset, y), (room.x0 + op.offset + op.width, y)
    if op.side == "W":
        x = room.x0
        return (x, room.y0 + op.offset), (x, room.y0 + op.offset + op.width)
    x = room.x1  # E
    return (x, room.y0 + op.offset), (x, room.y0 + op.offset + op.width)


def _draw_openings(dxf: DXF, room: Room, ox: float, oy: float) -> None:
    for op in room.openings:
        (ax, ay), (bx, by) = _opening_endpoints(room, op)
        ax, ay, bx, by = ax + ox, ay + oy, bx + ox, by + oy
        if op.kind == "opening":
            # ανοιχτό πέρασμα (λειτουργική επικοινωνία): μόνο παρειές, χωρίς φύλλο
            continue
        if op.kind == "window":
            # παράθυρο: γραμμή υαλοπίνακα + δύο μικρές παρειές
            dxf.line("OPENINGS", ax, ay, bx, by)
        else:
            # θύρα: φύλλο (γραμμή) + τόξο περιστροφής 90°
            r = op.width
            if op.side in ("S", "N"):
                dxf.line("OPENINGS", ax, ay, ax, ay + (r if op.side == "S" else -r))
                dxf.arc("OPENINGS", ax, ay, r, 0 if op.side == "S" else 270,
                        90 if op.side == "S" else 360)
            else:
                dxf.line("OPENINGS", ax, ay, ax + (r if op.side == "W" else -r), ay)
                dxf.arc("OPENINGS", ax, ay, r, 0, 90)


# ─────────────────────────── Σχεδίαση ενός ορόφου ─────────────────────────────

def _draw_floor(dxf: DXF, plan: FloorPlan, ox: float, oy: float) -> None:
    W, L, te = plan.width_ew, plan.length_ns, plan.ext_wall

    # Εξωτερικό περίγραμμα (ορθογωνισμένο πολύγωνο) + εσωτερική παρειά
    outline = plan.outline or [(0, 0), (W, 0), (W, L), (0, L)]
    dxf.polyline("OUTLINE", [(ox + x, oy + y) for (x, y) in outline], closed=True)
    for (cx0, cy0, cx1, cy1) in (plan.cells or [(0, 0, W, L)]):
        dxf.rect("WALLS", ox + cx0 + te, oy + cy0 + te,
                 ox + cx1 - te, oy + cy1 - te)

    # Χώροι (καθαρά ορθογώνια) + ονόματα/εμβαδά/διαστάσεις
    for room in plan.rooms:
        dxf.rect("ROOMS", ox + room.x0, oy + room.y0, ox + room.x1, oy + room.y1)
        cx, cy = ox + room.cx, oy + room.cy
        gw, gd = room_gross_dims(room, plan)
        dxf.text("TEXT", cx, cy + 0.28, 0.24, room.name)
        dxf.text("TEXT", cx, cy, 0.17,
                 f"{fmt(room.area)} m2  (kath.)")
        dxf.text("TEXT", cx, cy - 0.26, 0.15,
                 f"esot. {fmt(room.w)}x{fmt(room.d)}")
        dxf.text("TEXT", cx, cy - 0.50, 0.15,
                 f"mikt. {fmt(gw)}x{fmt(gd)}")
        _draw_openings(dxf, room, ox, oy)

    # Εξωτερικές συνολικές διαστάσεις (κάτω = πλάτος Α–Δ, αριστερά = μήκος Β–Ν)
    off = 1.2
    dxf.line("DIMS", ox, oy - off, ox + W, oy - off)
    dxf.line("DIMS", ox, oy - off + 0.15, ox, oy - off - 0.15)
    dxf.line("DIMS", ox + W, oy - off + 0.15, ox + W, oy - off - 0.15)
    dxf.text("DIMS", ox + W / 2, oy - off - 0.35, 0.28, f"{fmt(W)} m (A-D)")

    dxf.line("DIMS", ox - off, oy, ox - off, oy + L)
    dxf.line("DIMS", ox - off + 0.15, oy, ox - off - 0.15, oy)
    dxf.line("DIMS", ox - off + 0.15, oy + L, ox - off - 0.15, oy + L)
    dxf.text("DIMS", ox - off - 0.35, oy + L / 2, 0.28, f"{fmt(L)} m (B-N)", rot=90)

    # Τίτλος ορόφου
    dxf.text("TITLE", ox + W / 2, oy + L + 0.7, 0.4,
             f"{plan.floor_label}  -  {fmt(plan.footprint_area)} m2 (mikto)")


def _draw_north(dxf: DXF, x: float, y: float) -> None:
    """Βέλος Βορρά (πάντα προς +Y / πάνω)."""
    dxf.polyline("NORTH", [(x, y), (x - 0.35, y - 0.9), (x, y - 0.6),
                           (x + 0.35, y - 0.9)], closed=True)
    dxf.text("NORTH", x, y + 0.4, 0.45, "B")


# ─────────────────────────────── Δημόσιο API ─────────────────────────────────

def write_proposal_dxf(prop: Proposal, path: str) -> None:
    """Γράφει ένα DXF ανά πρόταση, με τους ορόφους δίπλα-δίπλα."""
    dxf = DXF()
    gap = 4.0
    ox = 0.0
    max_L = 0.0
    total_W = 0.0
    for plan in prop.floors:
        _draw_floor(dxf, plan, ox, 0.0)
        _draw_north(dxf, ox + plan.width_ew + 1.2, plan.length_ns)
        ox += plan.width_ew + gap
        max_L = max(max_L, plan.length_ns)
        total_W = ox

    # Υπόμνημα τίτλου πάνω από το σχέδιο
    dxf.text("TITLE", 0.0, max_L + 2.2, 0.5,
             f"{prop.spec.project_name} - {prop.title}", halign=0)
    dxf.text("TITLE", 0.0, max_L + 1.5, 0.30,
             f"{prop.spec.location}  |  Eisodos: {prop.spec.entrance.gr}  |  "
             f"Orofoi: {prop.spec.floors}", halign=0)

    data = dxf.render()
    # Κωδικοποίηση ANSI_1253 (ελληνικά)· ό,τι δεν χωρά → '?'
    with open(path, "wb") as f:
        f.write(data.encode("cp1253", errors="replace"))

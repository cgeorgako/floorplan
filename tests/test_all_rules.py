"""Γενικός έλεγχος συμμόρφωσης — ΟΛΕΣ οι οδηγίες του χρήστη.

Ένας συστηματικός έλεγχος (ανά κανόνα/οδηγία) που καλύπτει το σύνολο των
απαιτήσεων που έχουν δοθεί για τη γεννήτρια κατόψεων κατοικίας, από την αρχική
προδιαγραφή έως τις τελευταίες οδηγίες.

Εκτέλεση:  python tests/test_all_rules.py   (ή)  python -m pytest tests/
"""
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from floorplan_gen.models import BuildingSpec, Orientation, Category
from floorplan_gen.layout import generate_proposals, room_gross_dims, _door_between
from floorplan_gen.compliance import check_floor
from floorplan_gen import generator

BED_CATS = (Category.BEDROOM, Category.BEDROOM_MASTER)


# ─────────────────────────────── βοηθητικά ───────────────────────────────────

def spec(**kw) -> BuildingSpec:
    base = dict(
        max_width_ew=13.0, max_length_ns=11.0, entrance=Orientation.S, floors=1,
        ext_wall=0.30, int_wall=0.10, bedrooms=3, baths=1, wcs=1,
        has_storage=True, has_wardrobe=False, has_living=True, has_salon=True,
        has_big_kitchen=True, min_bedroom_side=3.0, max_total_area=150.0,
        num_proposals=3,
    )
    base.update(kw)
    return BuildingSpec(**base)


def all_floors(s):
    for p in generate_proposals(s):
        for fl in p.floors:
            yield p, fl


def rooms_of(fl, *cats):
    return [r for r in fl.rooms if r.category in cats]


def point_in_polygon(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xint = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xint:
                inside = not inside
    return inside


def dist_point_rect(px, py, r):
    dx = max(r.x0 - px, 0.0, px - r.x1)
    dy = max(r.y0 - py, 0.0, py - r.y1)
    return math.hypot(dx, dy)


# ─── R1. Είσοδοι → πλήθος προτάσεων & όροφοι (1-2) ────────────────────────────

def test_R1_proposal_count_and_floors():
    for n in (1, 2, 4, 6):
        props = generate_proposals(spec(num_proposals=n))
        assert len(props) == n
        assert all(len(p.floors) == 1 for p in props)
    props2 = generate_proposals(spec(floors=2, bedrooms=4, baths=2,
                                     max_total_area=200))
    assert all(len(p.floors) == 2 for p in props2)


# ─── R2. Βορράς πάντα πάνω (σύστημα Y↑ = Βορράς) ──────────────────────────────

def test_R2_north_is_up():
    # Οι συντεταγμένες αυξάνονται προς Βορρά· η ζώνη ημέρας (Ν) είναι κάτω και οι
    # χώροι νύχτας/υπνοδωμάτια (Β) πάνω → μεγαλύτερο μέσο Y από τη ζώνη ημέρας.
    for _, fl in all_floors(spec()):
        beds = rooms_of(fl, *BED_CATS)
        day = rooms_of(fl, Category.SALON, Category.LIVING, Category.KITCHEN)
        if beds and day:
            assert (sum(r.cy for r in beds) / len(beds)
                    > sum(r.cy for r in day) / len(day)), \
                "Τα υπνοδωμάτια (Βορράς) πρέπει να είναι πάνω (μεγαλύτερο Y)"
        # όλοι οι χώροι εντός του περιγράμματος [0,H] κατά Y
        for r in fl.rooms:
            assert -1e-6 <= r.y0 and r.y1 <= fl.length_ns + 1e-6


# ─── R3. Καθαρές & μικτές διαστάσεις χώρων ────────────────────────────────────

def test_R3_gross_and_net_dims():
    for _, fl in all_floors(spec()):
        for r in fl.rooms:
            gw, gd = room_gross_dims(r, fl)
            assert gw >= r.w - 1e-6 and gd >= r.d - 1e-6
            assert r.w > 0 and r.d > 0


# ─── R4. Έξοδοι PDF (με κλίμακα) + DXF ────────────────────────────────────────

def test_R4_pdf_and_dxf_outputs():
    import contextlib
    import io
    s = spec(num_proposals=2)
    s.project_name = "ΤεστΟδηγιών"
    with tempfile.TemporaryDirectory() as d:
        with contextlib.redirect_stdout(io.StringIO()):
            written = generator.run(s, outdir=d)
        pdfs = [p for p in written if p.endswith(".pdf")]
        dxfs = [p for p in written if p.endswith(".dxf")]
        assert len(pdfs) >= 3 and len(dxfs) == 2      # 2 προτάσεις + ενιαίο PDF
        for p in pdfs:
            assert os.path.getsize(p) > 1000
            with open(p, "rb") as fh:
                assert fh.read(5) == b"%PDF-"
        for p in dxfs:
            txt = open(p, encoding="cp1253", errors="ignore").read()
            assert "POLYLINE" in txt and "SECTION" in txt


# ─── R5. Εντός μέγιστου περιγράμματος & μέγιστου εμβαδού ───────────────────────

def test_R5_within_bounding_and_area():
    s = spec(max_width_ew=12.0, max_length_ns=10.0, max_total_area=115.0)
    for _, fl in all_floors(s):
        assert fl.width_ew <= s.max_width_ew + 1e-6
        assert fl.length_ns <= s.max_length_ns + 1e-6
        assert fl.footprint_area <= s.max_total_area + 1.0


# ─── R6/R17. Τύποι περιγράμματος Γ / Τ / Ζ / ορθογώνιο & αυτοσχεδιασμός ─────────

def test_R6_shapes_gamma_tau_rect():
    assert len(generate_proposals(spec(footprint_shape="L"))[0].floors[0].outline) == 6
    assert len(generate_proposals(spec(footprint_shape="T"))[0].floors[0].outline) == 8
    assert len(generate_proposals(spec(footprint_shape="rectangular"))[0]
               .floors[0].outline) == 4


def _staggered(o):
    minx = min(x for x, _ in o)
    bottom_minx = min((x for x, y in o if abs(y) < 0.05), default=minx)
    top_y = max(y for _, y in o)
    top_maxx = max((x for x, y in o if abs(y - top_y) < 0.05), default=0)
    maxx = max(x for x, _ in o)
    return bottom_minx > minx + 0.3 and top_maxx < maxx - 0.3


def test_R17_auto_more_polygonal_incl_Z():
    props = generate_proposals(spec(footprint_shape="auto", num_proposals=3))
    verts = {len(p.floors[0].outline) for p in props}
    assert 6 in verts and 8 in verts               # Γ και Τ/Ζ
    assert any(_staggered(p.floors[0].outline) for p in props), \
        "Ο αυτοσχεδιασμός πρέπει να παράγει και κλιμακωτό (Ζ) σχήμα"
    # ρητό Ζ
    assert _staggered(generate_proposals(spec(footprint_shape="Z"))[0]
                      .floors[0].outline)


def test_R6_only_orthogonal_edges():
    for shape in ("auto", "L", "T", "Z", "rectangular"):
        for _, fl in all_floors(spec(footprint_shape=shape)):
            o = fl.outline
            for i in range(len(o)):
                x0, y0 = o[i]
                x1, y1 = o[(i + 1) % len(o)]
                assert abs(x0 - x1) < 1e-6 or abs(y0 - y1) < 1e-6, \
                    f"{shape}: μη ορθογώνια ακμή"


# ─── R7. Υπνοδωμάτια ≥ 3,00×3,00 · master ≥ 3,50 ──────────────────────────────

def test_R7_bedroom_min_sides():
    for _, fl in all_floors(spec()):
        for r in rooms_of(fl, *BED_CATS):
            assert min(r.w, r.d) >= 3.00 - 0.05, f"{r.name} {r.w:.2f}×{r.d:.2f}"
        for r in rooms_of(fl, Category.BEDROOM_MASTER):
            assert min(r.w, r.d) >= 3.50 - 0.05, f"master {r.w:.2f}×{r.d:.2f}"


# ─── R8. Σαλόνι ελάχιστη διάσταση 3,50 ────────────────────────────────────────

def test_R8_salon_min_dimension():
    for _, fl in all_floors(spec()):
        for r in rooms_of(fl, Category.SALON):
            assert min(r.w, r.d) >= 3.50 - 0.05, f"σαλόνι {r.w:.2f}×{r.d:.2f}"


# ─── R9. Κουζίνα δεν είναι υποχρεωτικά ίδιο πλάτος με σαλόνι ───────────────────

def test_R9_kitchen_width_independent_of_salon():
    differ = False
    for _, fl in all_floors(spec()):
        s = rooms_of(fl, Category.SALON)
        k = rooms_of(fl, Category.KITCHEN)
        if s and k and abs(s[0].w - k[0].w) > 0.05:
            differ = True
    assert differ, "Η κουζίνα πρέπει να μπορεί να έχει διαφορετικό πλάτος από το σαλόνι"


# ─── R10. Αποθήκη ≤ 2,00 μ. σε κάθε κατεύθυνση ────────────────────────────────

def test_R10_storage_max_200():
    for _, fl in all_floors(spec(has_storage=True)):
        for r in rooms_of(fl, Category.STORAGE):
            assert max(r.w, r.d) <= 2.00 + 0.03, f"αποθήκη {r.w:.2f}×{r.d:.2f}"


# ─── R11. Προτεραιότητες: (α) υ/δ, (β) ελάχ. διάδρομος, (γ) μεγ. σαλόνι ────────

def test_R11a_bedrooms_priority():
    # (α) τα υπνοδωμάτια τηρούν τις ελάχιστες διαστάσεις ακόμη & σε πιεσμένο περίγρ.
    for _, fl in all_floors(spec(max_width_ew=11.5, max_length_ns=10.0,
                                 max_total_area=118.0)):
        for r in rooms_of(fl, *BED_CATS):
            assert min(r.w, r.d) >= 3.00 - 0.06


def test_R11b_corridor_minimized():
    # (β) ο διάδρομος ≤ ~16% της καθαρής επιφάνειας
    for _, fl in all_floors(spec()):
        corr = sum(r.area for r in rooms_of(fl, Category.CORRIDOR))
        assert corr <= 0.16 * fl.net_area + 1e-6, f"διάδρομος {corr:.1f} m²"


def test_R11c_salon_maximised_over_kitchen():
    # (γ) το σαλόνι μεγιστοποιείται → φαρδύτερο/ίσο με την κουζίνα
    for _, fl in all_floors(spec()):
        s = rooms_of(fl, Category.SALON)
        k = rooms_of(fl, Category.KITCHEN)
        if s and k:
            assert s[0].w >= k[0].w - 0.01


# ─── R12. Χωλ: προαιρετικός, μεταβλητή θέση, πλάτος ≤ 1,30 ─────────────────────

def test_R12_hall_optional_varies_and_width():
    props = generate_proposals(spec(has_hall=True, num_proposals=3))
    has = [bool(rooms_of(p.floors[0], Category.HALL)) for p in props]
    assert any(has) and not all(has), "Ο χωλ μπαίνει σε ΜΕΡΙΚΕΣ μόνο λύσεις"
    # χωρίς χωλ → πουθενά
    for _, fl in all_floors(spec(has_hall=False)):
        assert not rooms_of(fl, Category.HALL)
    # μέγιστο πλάτος 1,30
    for _, fl in all_floors(spec(has_hall=True, num_proposals=6)):
        for r in rooms_of(fl, Category.HALL):
            assert r.w <= 1.30 + 0.02, f"χωλ πλάτος {r.w:.2f} > 1,30"


# ─── R13. Λουτρό ΠΑΝΤΑ εξωτ. φως · WC εξωτ. αν εφικτό ─────────────────────────

def test_R13_bath_always_exterior_wc_when_feasible():
    for shape in ("auto", "L", "T", "Z", "rectangular"):
        for _, fl in all_floors(spec(footprint_shape=shape, num_proposals=3)):
            for r in rooms_of(fl, Category.BATH):
                assert r.ext_sides, f"{shape}: λουτρό χωρίς εξωτ. όψη"
                # έχει και παράθυρο προς τα έξω
                assert any(o.kind == "window" for o in r.openings), \
                    f"{shape}: λουτρό χωρίς παράθυρο"
    # Το WC συνήθως αποκτά εξωτερική όψη (εφικτό) σε άνετο περίγραμμα
    wc_ext = 0
    wc_tot = 0
    for _, fl in all_floors(spec(num_proposals=3)):
        for r in rooms_of(fl, Category.WC):
            wc_tot += 1
            wc_ext += 1 if r.ext_sides else 0
    assert wc_tot == 0 or wc_ext >= 1


# ─── R14. Κάθε χώρος έχει επικοινωνία (θύρα/άνοιγμα) ──────────────────────────

def test_R14_every_room_has_access():
    for shape in ("auto", "L", "T", "Z", "rectangular"):
        for _, fl in all_floors(spec(footprint_shape=shape, num_proposals=3)):
            for r in fl.rooms:
                if r.category == Category.STAIRS or not r.name:
                    continue
                assert r.openings, f"{shape}/{r.name}: χώρος χωρίς επικοινωνία"


# ─── R15. Κανένα άνοιγμα σε κάθετο τοίχο (μακριά από γωνίες) ───────────────────

def test_R15_openings_clear_of_corners():
    for shape in ("auto", "L", "T", "Z"):
        for _, fl in all_floors(spec(footprint_shape=shape, num_proposals=3)):
            for r in fl.rooms:
                for op in r.openings:
                    seg = r.w if op.side in ("N", "S") else r.d
                    assert op.offset >= 0.10 - 1e-6, \
                        f"{r.name}:{op.side} άνοιγμα στη γωνία"
                    assert op.offset + op.width <= seg - 0.10 + 1e-6, \
                        f"{r.name}:{op.side} άνοιγμα στη γωνία"


# ─── R16. Εξωτ. τοίχος σε πλευρά προς ύπαιθρο σημειώνεται (πάχος te/ti σωστό) ──

def test_R16_boundary_sides_marked():
    for shape in ("auto", "L", "T", "Z", "rectangular"):
        for _, fl in all_floors(spec(footprint_shape=shape)):
            d = fl.ext_wall + fl.int_wall + 0.05
            cells = fl.cells

            def inside(x, y):
                return any(cx0 - 1e-6 <= x <= cx1 + 1e-6 and
                           cy0 - 1e-6 <= y <= cy1 + 1e-6
                           for (cx0, cy0, cx1, cy1) in cells)

            for r in fl.rooms:
                if r.category == Category.CORRIDOR or not r.name:
                    continue
                for side, px, py in (("N", r.cx, r.y1 + d), ("S", r.cx, r.y0 - d),
                                     ("E", r.x1 + d, r.cy), ("W", r.x0 - d, r.cy)):
                    if not inside(px, py):
                        assert side in r.ext_sides, \
                            f"{shape}/{r.name}:{side} λεπτός εξωτ. τοίχος"


# ─── R18. Καμία γκρι νεκρή ζώνη στο εσωτερικό (ιδίως χωρίς αποθήκη/χωλ) ────────

def test_R18_no_interior_dead_zone():
    # Δειγματοληψία εσωτερικών σημείων: κανένα σημείο βαθιά μέσα στο περίγραμμα
    # δεν πρέπει να μένει ακάλυπτο (μακριά από κάθε χώρο > πάχος εξωτ. τοίχου).
    configs = [
        spec(has_storage=False, has_hall=False, num_proposals=3),
        spec(has_storage=False, has_hall=True, num_proposals=3),
        spec(has_storage=True, has_hall=True, num_proposals=3),
        spec(footprint_shape="Z", num_proposals=3),
    ]
    step = 0.30
    for s in configs:
        for _, fl in all_floors(s):
            o = fl.outline
            xs = [x for x, _ in o]
            ys = [y for _, y in o]
            dead = 0
            x = min(xs) + step
            while x < max(xs):
                y = min(ys) + step
                while y < max(ys):
                    if point_in_polygon(x, y, o):
                        # ΟΛΟΙ οι χώροι (και οι ανώνυμες προεκτάσεις διαδρόμου)
                        dmin = min((dist_point_rect(x, y, r) for r in fl.rooms),
                                   default=9.9)
                        if dmin > fl.ext_wall + 0.05:   # βαθιά νεκρή ζώνη
                            dead += 1
                    y += step
                x += step
            assert dead == 0, f"Νεκρή (γκρι) ζώνη: {dead} σημεία ({fl.floor_label})"


# ─── R19. Μη επικάλυψη χώρων ──────────────────────────────────────────────────

def test_R19_rooms_non_overlapping():
    for shape in ("auto", "L", "T", "Z", "rectangular"):
        for _, fl in all_floors(spec(footprint_shape=shape)):
            rr = fl.rooms
            for i in range(len(rr)):
                for j in range(i + 1, len(rr)):
                    a, b = rr[i], rr[j]
                    ov = (a.x0 < b.x1 - 1e-6 and b.x0 < a.x1 - 1e-6 and
                          a.y0 < b.y1 - 1e-6 and b.y0 < a.y1 - 1e-6)
                    assert not ov, f"{shape}: επικάλυψη {a.name}/{b.name}"


# ─── R20. Ημέρα: ανοιχτή επικοινωνία (καθιστικό↔σαλόνι↔κουζίνα) ────────────────

def test_R20_day_zone_open_plan():
    for _, fl in all_floors(spec()):
        openings = [op for r in fl.rooms for op in r.openings
                    if op.kind == "opening"]
        assert len(openings) >= 1


# ─── R21. Έλεγχοι πολεοδομικής συμμόρφωσης εκτελούνται ────────────────────────

def test_R21_compliance_report_runs():
    for _, fl in all_floors(spec()):
        rows = check_floor(fl)
        assert rows and all(r.net_area > 0 for r in rows)


# ─── R22. ΕΠΙΚΟΙΝΩΝΙΑ: κάθε χώρος προσβάσιμος από τη ζώνη ημέρας (σαλόνι→υ/δ) ──

def _unreachable_from_day(fl):
    rooms = fl.rooms
    n = len(rooms)
    ti, te = fl.int_wall, fl.ext_wall
    adj = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            if _door_between(rooms[i], rooms[j], ti, te):
                adj[i].add(j)
                adj[j].add(i)
    seed = next((i for i, r in enumerate(rooms)
                 if r.category in (Category.SALON, Category.LIVING,
                                   Category.KITCHEN)), 0)
    seen, st = set(), [seed]
    while st:
        u = st.pop()
        if u in seen:
            continue
        seen.add(u)
        st += [v for v in adj[u] if v not in seen]
    return [rooms[i].name for i in range(n) if i not in seen and rooms[i].name]


def test_R22_all_rooms_reachable_from_salon():
    # Πρέπει να υπάρχει διαδρομή σαλόνι → διάδρομος → ΚΑΘΕ υπνοδωμάτιο/χώρο.
    for beds, baths, wcs in ((2, 1, 0), (3, 1, 1), (3, 2, 1), (4, 2, 1),
                             (2, 1, 1), (5, 2, 2)):
        for sto in (True, False):
            for hall in (True, False):
                for shape in ("auto", "Z", "L", "T", "rectangular"):
                    s = spec(bedrooms=beds, baths=baths, wcs=wcs,
                             has_storage=sto, has_hall=hall,
                             footprint_shape=shape, max_width_ew=14.0,
                             max_length_ns=12.0, max_total_area=220.0)
                    for _, fl in all_floors(s):
                        unr = _unreachable_from_day(fl)
                        assert not unr, (f"b{beds} ba{baths} wc{wcs} {shape}: "
                                         f"αποκομμένοι χώροι {unr}")


# ─── R23. Λουτρό & WC: ΤΟ ΠΟΛΥ μία εσωτερική θύρα (όχι δύο) ────────────────────

def test_R23_bath_wc_single_interior_door():
    for beds, baths, wcs in ((3, 1, 1), (3, 2, 1), (4, 2, 2), (2, 1, 0)):
        for shape in ("auto", "Z", "L", "T", "rectangular"):
            s = spec(bedrooms=beds, baths=baths, wcs=wcs,
                     footprint_shape=shape, max_width_ew=14.0,
                     max_length_ns=12.0, max_total_area=220.0)
            for _, fl in all_floors(s):
                for r in fl.rooms:
                    if r.category in (Category.BATH, Category.WC):
                        ndoors = sum(1 for o in r.openings
                                     if o.kind == "door" and not o.to_exterior)
                        assert ndoors <= 1, (f"{shape}/{r.name}: {ndoors} "
                                             f"εσωτερικές θύρες (>1)")


# ─── R24. Σαλόνι & κουζίνα: όχι πάντα ίδιο πλάτος/μήκος ───────────────────────

def test_R24_salon_kitchen_differ():
    # Το πλάτος τους διαφέρει ΠΑΝΤΑ· σε πολυγωνικά περιγράμματα διαφέρει και το
    # μήκος (βάθος) — άρα δεν έχουν πάντα ίδιες διαστάσεις.
    diff_len = False
    for shape in ("auto", "Z"):
        for _, fl in all_floors(spec(footprint_shape=shape, num_proposals=3)):
            s = rooms_of(fl, Category.SALON)
            k = rooms_of(fl, Category.KITCHEN)
            if s and k:
                assert abs(s[0].w - k[0].w) > 0.05, "ίδιο πλάτος σαλονιού/κουζίνας"
                if abs(s[0].d - k[0].d) > 0.05:
                    diff_len = True
    assert diff_len, "Σαλόνι & κουζίνα πρέπει να μπορούν να διαφέρουν και σε μήκος"


# ─── R25. Διάδρομος: ελάχιστο μήκος & δεν εφάπτεται στους δύο πλαϊνούς τοίχους ─

def test_R25_corridor_not_touching_both_side_walls():
    # Στη συμπαγή διάταξη (≥3 βοηθητικοί) ο διάδρομος είναι εσοχή: δεν αγγίζει
    # ΚΑΙ τον ανατολικό ΚΑΙ τον δυτικό εξωτερικό τοίχο.
    for _, fl in all_floors(spec(bedrooms=3, baths=1, wcs=1, has_storage=True,
                                 has_hall=True, num_proposals=3)):
        corr = [r for r in fl.rooms
                if r.category == Category.CORRIDOR and r.name]
        for c in corr:
            touches_w = c.x0 <= fl.ext_wall + 0.06
            touches_e = c.x1 >= fl.width_ew - fl.ext_wall - 0.06
            assert not (touches_w and touches_e), \
                "Ο διάδρομος εφάπτεται και στους δύο πλαϊνούς εξωτ. τοίχους"


if __name__ == "__main__":
    fns = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    ok = 0
    for name, fn in fns:
        fn()
        print(f"✓ {name}")
        ok += 1
    print(f"\nΌλες οι οδηγίες επαληθεύτηκαν ({ok} έλεγχοι).")

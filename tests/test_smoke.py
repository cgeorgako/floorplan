"""Στοιχειώδεις έλεγχοι λειτουργικότητας της γεννήτριας κατόψεων.

Εκτέλεση:  python -m pytest tests/  (ή)  python tests/test_smoke.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from floorplan_gen.models import BuildingSpec, Orientation, Category
from floorplan_gen.layout import generate_proposals, room_gross_dims
from floorplan_gen.compliance import check_floor


def _spec(**kw):
    base = dict(
        max_width_ew=13.0, max_length_ns=10.0, entrance=Orientation.S, floors=1,
        ext_wall=0.30, int_wall=0.10, bedrooms=3, baths=1, wcs=1, has_storage=True,
        has_wardrobe=False, has_living=True, has_salon=True, has_big_kitchen=True,
        min_bedroom_side=3.0, max_total_area=130.0, num_proposals=3,
    )
    base.update(kw)
    return BuildingSpec(**base)


def test_generates_requested_count():
    props = generate_proposals(_spec(num_proposals=4))
    assert len(props) == 4
    for p in props:
        assert len(p.floors) == 1


def test_two_floors():
    props = generate_proposals(_spec(floors=2, bedrooms=4, baths=2,
                                     max_total_area=180))
    assert all(len(p.floors) == 2 for p in props)


def test_rooms_within_footprint_and_nonoverlapping():
    for p in generate_proposals(_spec()):
        for fl in p.floors:
            for r in fl.rooms:
                assert fl.ext_wall - 1e-6 <= r.x0 < r.x1 <= fl.width_ew - fl.ext_wall + 1e-6
                assert fl.ext_wall - 1e-6 <= r.y0 < r.y1 <= fl.length_ns - fl.ext_wall + 1e-6
            # μη επικάλυψη ζευγών (καθαρά ορθογώνια)
            rr = fl.rooms
            for i in range(len(rr)):
                for j in range(i + 1, len(rr)):
                    a, b = rr[i], rr[j]
                    overlap = (a.x0 < b.x1 - 1e-6 and b.x0 < a.x1 - 1e-6 and
                               a.y0 < b.y1 - 1e-6 and b.y0 < a.y1 - 1e-6)
                    assert not overlap, f"Επικάλυψη: {a.name} με {b.name}"


def test_footprint_within_limits():
    s = _spec(max_total_area=120.0)
    for p in generate_proposals(s):
        fl = p.floors[0]
        assert fl.width_ew <= s.max_width_ew + 1e-6
        assert fl.length_ns <= s.max_length_ns + 1e-6
        assert fl.footprint_area <= s.max_total_area + 1.0


def test_bedrooms_meet_min_side():
    # με άνετο περίγραμμα, όλα τα υπνοδωμάτια πρέπει να πληρούν 3,00×3,00
    for p in generate_proposals(_spec()):
        for fl in p.floors:
            for r in fl.rooms:
                if r.category in (Category.BEDROOM, Category.BEDROOM_MASTER):
                    assert min(r.w, r.d) >= 3.0 - 0.05, f"{r.name} {r.w:.2f}×{r.d:.2f}"


def test_auto_improvises_shapes():
    # «auto» → διαφορετικοί τύποι ανά πρόταση (Γ=6 κορυφές, Τ=8 κορυφές)
    props = generate_proposals(_spec(footprint_shape="auto", num_proposals=3))
    verts = {len(p.floors[0].outline) for p in props}
    assert 6 in verts, "Δεν παρήχθη Γ-σχήμα"
    assert 8 in verts, "Δεν παρήχθη Τ-σχήμα"


def test_shape_T_gives_8_vertices():
    p = generate_proposals(_spec(footprint_shape="T"))[0]
    assert len(p.floors[0].outline) == 8


def test_shape_L_gives_6_vertices():
    p = generate_proposals(_spec(footprint_shape="L"))[0]
    assert len(p.floors[0].outline) == 6


def test_rectangular_override():
    p = generate_proposals(_spec(footprint_shape="rectangular"))[0]
    assert len(p.floors[0].outline) == 4


def test_no_curves_only_orthogonal():
    # κάθε ακμή του περιγράμματος είναι οριζόντια ή κατακόρυφη (χωρίς καμπύλες)
    for p in generate_proposals(_spec()):
        o = p.floors[0].outline
        for i in range(len(o)):
            x0, y0 = o[i]
            x1, y1 = o[(i + 1) % len(o)]
            assert abs(x0 - x1) < 1e-6 or abs(y0 - y1) < 1e-6


def test_day_zone_open_communication():
    # καθιστικό↔σαλόνι↔κουζίνα: ανοιχτά περάσματα (kind="opening")
    p = generate_proposals(_spec())[0]
    openings = [op for r in p.floors[0].rooms for op in r.openings
                if op.kind == "opening"]
    assert len(openings) >= 2, "Λείπει η λειτουργική επικοινωνία ζώνης ημέρας"


def test_corridor_is_minimized():
    # ο διάδρομος να μένει κάτω από ~16% της καθαρής επιφάνειας (Α.6.2)
    for p in generate_proposals(_spec()):
        for fl in p.floors:
            corr = sum(r.area for r in fl.rooms if r.category == Category.CORRIDOR)
            assert corr <= 0.16 * fl.net_area + 1e-6, \
                f"Διάδρομος {corr:.1f} m² > 16% του καθαρού"


def test_boundary_sides_marked_exterior():
    # κάθε πλευρά χώρου που βλέπει στο εξωτερικό (εκτός περιγράμματος) πρέπει να
    # είναι σημειωμένη ως εξωτερική → σχεδιάζεται με παχύ τοίχο (te).
    for p in generate_proposals(_spec()):
        fl = p.floors[0]
        d = fl.ext_wall + fl.int_wall + 0.05
        cells = fl.cells

        def inside(x, y):
            return any(cx0 - 1e-6 <= x <= cx1 + 1e-6 and cy0 - 1e-6 <= y <= cy1 + 1e-6
                       for (cx0, cy0, cx1, cy1) in cells)

        for r in fl.rooms:
            if r.category == Category.CORRIDOR:
                continue
            for side, px, py in (("N", r.cx, r.y1 + d), ("S", r.cx, r.y0 - d),
                                 ("E", r.x1 + d, r.cy), ("W", r.x0 - d, r.cy)):
                if not inside(px, py):        # δεν υπάρχει κτίριο πέρα → περίγραμμα
                    assert side in r.ext_sides, f"{r.name}:{side} λεπτός εξωτ. τοίχος"


def test_corridor_compact():
    # ο συμπαγής διάδρομος να μην φτάνει το πλήρες πλάτος της ζώνης νύχτας
    p = generate_proposals(_spec())[0]
    fl = p.floors[0]
    corr = next((r for r in fl.rooms if r.category == Category.CORRIDOR), None)
    assert corr is not None
    assert corr.w < fl.width_ew - 2.0, "Ο διάδρομος δεν ελαχιστοποιήθηκε"


def test_compliance_runs():
    p = generate_proposals(_spec())[0]
    rows = check_floor(p.floors[0])
    assert rows and all(r.net_area > 0 for r in rows)


def test_gross_ge_net():
    p = generate_proposals(_spec())[0]
    for r in p.floors[0].rooms:
        gw, gd = room_gross_dims(r, p.floors[0])
        assert gw >= r.w - 1e-6 and gd >= r.d - 1e-6


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"✓ {fn.__name__}")
    print(f"\nΌλοι οι έλεγχοι πέρασαν ({len(fns)}).")

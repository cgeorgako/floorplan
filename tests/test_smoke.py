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

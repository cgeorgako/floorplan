"""Διεπαφή γραμμής εντολών — διαδραστική συλλογή δεδομένων ή από JSON.

Χρήση:
  python -m floorplan_gen                      # διαδραστικά (ερωτήσεις)
  python -m floorplan_gen --config config.json # από αρχείο JSON
  python -m floorplan_gen --config c.json --out out_dir
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from .models import BuildingSpec, Orientation
from .generator import run


# ─────────────────────────── είσοδος από JSON ─────────────────────────────────

def spec_from_dict(d: Dict[str, Any]) -> BuildingSpec:
    return BuildingSpec(
        max_width_ew=float(d["max_width_ew"]),
        max_length_ns=float(d["max_length_ns"]),
        entrance=Orientation.parse(str(d["entrance"])),
        floors=int(d["floors"]),
        ext_wall=float(d["ext_wall"]),
        int_wall=float(d["int_wall"]),
        bedrooms=int(d["bedrooms"]),
        baths=int(d.get("baths", 1)),
        wcs=int(d.get("wcs", 0)),
        has_storage=bool(d.get("has_storage", False)),
        has_wardrobe=bool(d.get("has_wardrobe", False)),
        has_hall=bool(d.get("has_hall", True)),
        has_living=bool(d.get("has_living", True)),
        has_salon=bool(d.get("has_salon", False)),
        has_big_kitchen=bool(d.get("has_big_kitchen", False)),
        min_bedroom_side=float(d.get("min_bedroom_side", 3.0)),
        max_total_area=float(d["max_total_area"]),
        num_proposals=int(d.get("num_proposals", 3)),
        footprint_shape=str(d.get("footprint_shape", "polygonal")),
        project_name=str(d.get("project_name", "Κατοικία")),
        client=str(d.get("client", "")),
        location=str(d.get("location", "Αμαλιάδα, Π.Ε. Ηλείας")),
    )


# ─────────────────────────── διαδραστική είσοδος ──────────────────────────────

def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default != "" else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val if val else default


def _ask_float(prompt: str, default: float) -> float:
    while True:
        raw = _ask(prompt, str(default)).replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            print("  ✗ Δώσε αριθμό.")


def _ask_int(prompt: str, default: int) -> int:
    while True:
        raw = _ask(prompt, str(default))
        try:
            return int(raw)
        except ValueError:
            print("  ✗ Δώσε ακέραιο.")


def _ask_bool(prompt: str, default: bool) -> bool:
    d = "ναι" if default else "όχι"
    raw = _ask(prompt + " (ναι/όχι)", d).lower()
    return raw in ("ναι", "ν", "yes", "y", "1", "true", "nai")


def interactive_spec() -> BuildingSpec:
    print("\n=== Γεννήτρια προτάσεων κατόψεων κατοικίας ===")
    print("Τεχνικό Γραφείο Μελετών — Γεωργακόπουλος Χρ. / Φουντάς Αθ.")
    print("(Enter = προεπιλεγμένη τιμή)\n")

    name = _ask("Ονομασία έργου", "Κατοικία")
    w = _ask_float("Μέγιστο πλάτος περιγράμματος Ανατολή–Δύση (m)", 13.0)
    l = _ask_float("Μέγιστο μήκος περιγράμματος Βορρά–Νότο (m)", 10.0)
    shape = _ask("Σχήμα περιγράμματος: αυτόματο / Γ / Τ / ορθογώνιο", "αυτόματο")
    ent = _ask("Προσανατολισμός κύριας εισόδου (Β/Ν/Α/Δ)", "Ν")
    floors = _ask_int("Όροφοι — 1 (ισόγειο) ή 2 (διώροφο)", 1)
    ext = _ask_float("Πάχος εξωτερικής τοιχοποιίας (m)", 0.30)
    inn = _ask_float("Πάχος εσωτερικής τοιχοποιίας (m)", 0.10)
    beds = _ask_int("Πλήθος υπνοδωματίων", 3)
    baths = _ask_int("Πλήθος λουτρών", 1)
    wcs = _ask_int("Πλήθος WC", 1)
    storage = _ask_bool("Οικιακή αποθήκη;", True)
    wardrobe = _ask_bool("Χώρος βεστιαρίου;", False)
    hall = _ask_bool("Χώρος υποδοχής (χωλ) — προαιρετικός, όχι σε όλες τις λύσεις;", True)
    living = _ask_bool("Καθιστικό;", True)
    salon = _ask_bool("Σαλόνι;", True)
    big_kitchen = _ask_bool("Μεγάλη κουζίνα;", True)
    min_side = _ask_float("Ελάχιστη πλευρά υπνοδωματίου (m)", 3.0)
    max_area = _ask_float("Μέγιστο εμβαδόν ΜΕ τοίχους (m²)", 100.0)
    n = _ask_int("Πλήθος προτάσεων-λύσεων", 3)

    return BuildingSpec(
        max_width_ew=w, max_length_ns=l, entrance=Orientation.parse(ent),
        floors=floors, ext_wall=ext, int_wall=inn, bedrooms=beds, baths=baths,
        wcs=wcs, has_storage=storage, has_wardrobe=wardrobe, has_living=living,
        has_salon=salon, has_big_kitchen=big_kitchen, min_bedroom_side=min_side,
        max_total_area=max_area, num_proposals=n, footprint_shape=shape,
        has_hall=hall, project_name=name,
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Γεννήτρια προτάσεων κατόψεων κατοικίας (PDF + DXF).")
    ap.add_argument("--config", help="Αρχείο JSON με τα δεδομένα εισόδου.")
    ap.add_argument("--out", default="out", help="Φάκελος εξόδου (default: out).")
    args = ap.parse_args(argv)

    if args.config:
        with open(args.config, encoding="utf-8") as f:
            spec = spec_from_dict(json.load(f))
    else:
        try:
            spec = interactive_spec()
        except (EOFError, KeyboardInterrupt):
            print("\nΑκυρώθηκε.")
            return 1

    try:
        run(spec, args.out)
    except ValueError as e:
        print(f"\n✗ {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

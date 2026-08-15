"""Ενορχήστρωση: από BuildingSpec → αρχεία PDF & DXF."""
from __future__ import annotations

import os
from typing import List

from .layout import generate_proposals
from .models import BuildingSpec, Proposal
from .dxf_writer import write_proposal_dxf
from .pdf_writer import write_proposal_pdf, write_all_pdf
from .textutil import fmt


def _slug(s: str) -> str:
    keep = []
    for ch in s:
        if ch.isalnum():
            keep.append(ch)
        elif ch in " -_":
            keep.append("_")
    return ("".join(keep).strip("_") or "katopsi")[:40]


def run(spec: BuildingSpec, outdir: str = "out") -> List[str]:
    """Παράγει τις προτάσεις και γράφει PDF + DXF. Επιστρέφει τα paths."""
    os.makedirs(outdir, exist_ok=True)
    proposals = generate_proposals(spec)
    base = _slug(spec.project_name)
    written: List[str] = []

    for prop in proposals:
        pdf_path = os.path.join(outdir, f"{base}_protasi_{prop.index}.pdf")
        dxf_path = os.path.join(outdir, f"{base}_protasi_{prop.index}.dxf")
        write_proposal_pdf(prop, pdf_path)
        write_proposal_dxf(prop, dxf_path)
        written += [pdf_path, dxf_path]

    # Ενιαίο PDF με όλες τις προτάσεις
    all_pdf = os.path.join(outdir, f"{base}_ola.pdf")
    write_all_pdf(proposals, all_pdf)
    written.append(all_pdf)

    _print_report(spec, proposals, written)
    return written


def _print_report(spec: BuildingSpec, proposals: List[Proposal],
                  written: List[str]) -> None:
    print("\n" + "═" * 68)
    print(f"  {spec.project_name} — {len(proposals)} προτάσεις κατόψεων")
    print("═" * 68)
    print(f"  Περίγραμμα (μέγ.): {fmt(spec.max_width_ew)} × "
          f"{fmt(spec.max_length_ns)} m  |  Μέγ. εμβ.: {fmt(spec.max_total_area)} m²")
    print(f"  Είσοδος: {spec.entrance.gr}  |  Όροφοι: {spec.floors}  |  "
          f"Υ/Δ: {spec.bedrooms}  Λουτρά: {spec.baths}  WC: {spec.wcs}")
    print(f"  Τοιχοποιία: εξωτ. {fmt(spec.ext_wall)} m / εσωτ. {fmt(spec.int_wall)} m")
    print("─" * 68)
    for prop in proposals:
        dims = " + ".join(f"{fmt(fl.width_ew)}×{fmt(fl.length_ns)}"
                          for fl in prop.floors)
        gross = sum(fl.footprint_area for fl in prop.floors)
        print(f"  {prop.title}: {dims} m  |  μικτό {fmt(gross)} m²"
              + ("  ⚠" if prop.warnings else ""))
        for wn in prop.warnings:
            print(f"      ⚠ {wn}")
    print("─" * 68)
    print("  Αρχεία:")
    for p in written:
        print(f"    • {p}")
    print("═" * 68 + "\n")

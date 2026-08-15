"""Flask web διεπαφή για τη γεννήτρια προτάσεων κατόψεων κατοικίας.

Ροή: φόρμα HTML → συλλογή δεδομένων → εκτέλεση της Python γεννήτριας →
παραγωγή PDF (σε κλίμακα) + DXF (R12) → σελίδα αποτελεσμάτων με προεπισκόπηση
και συνδέσμους λήψης.

Εκτέλεση:
    python -m webapp.app         (ή)   python webapp/app.py
    → άνοιξε http://127.0.0.1:5000
"""
from __future__ import annotations

import os
import sys
import uuid

from flask import (Flask, abort, render_template, request,
                   send_from_directory, url_for)

# εξασφάλισε ότι το πακέτο floorplan_gen είναι στο path (root του repo)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from floorplan_gen.models import BuildingSpec, Orientation           # noqa: E402
from floorplan_gen.layout import generate_proposals                  # noqa: E402
from floorplan_gen.dxf_writer import write_proposal_dxf              # noqa: E402
from floorplan_gen.pdf_writer import write_proposal_pdf, write_all_pdf  # noqa: E402
from floorplan_gen.generator import _slug                            # noqa: E402

try:
    import pymupdf                       # για προεπισκόπηση PNG (προαιρετικό)
    _HAS_PYMUPDF = True
except Exception:                        # pragma: no cover
    _HAS_PYMUPDF = False

app = Flask(__name__)
OUT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "out")
os.makedirs(OUT_ROOT, exist_ok=True)


# ─────────────────────────── ανάγνωση φόρμας ──────────────────────────────────

def _f(name: str, default: float) -> float:
    raw = (request.form.get(name, "") or "").strip().replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return default


def _i(name: str, default: int) -> int:
    raw = (request.form.get(name, "") or "").strip()
    try:
        return int(float(raw))
    except ValueError:
        return default


def _b(name: str) -> bool:
    return request.form.get(name) in ("on", "1", "true", "ναι", "yes")


def spec_from_form() -> BuildingSpec:
    return BuildingSpec(
        project_name=(request.form.get("project_name") or "Κατοικία").strip(),
        location=(request.form.get("location") or "Αμαλιάδα, Π.Ε. Ηλείας").strip(),
        max_width_ew=_f("max_width_ew", 13.0),
        max_length_ns=_f("max_length_ns", 10.0),
        footprint_shape=(request.form.get("footprint_shape") or "polygonal"),
        entrance=Orientation.parse(request.form.get("entrance") or "Ν"),
        floors=_i("floors", 1),
        ext_wall=_f("ext_wall", 0.30),
        int_wall=_f("int_wall", 0.10),
        bedrooms=_i("bedrooms", 3),
        baths=_i("baths", 1),
        wcs=_i("wcs", 1),
        has_storage=_b("has_storage"),
        has_wardrobe=_b("has_wardrobe"),
        has_living=_b("has_living"),
        has_salon=_b("has_salon"),
        has_big_kitchen=_b("has_big_kitchen"),
        min_bedroom_side=_f("min_bedroom_side", 3.0),
        max_total_area=_f("max_total_area", 130.0),
        num_proposals=_i("num_proposals", 3),
    )


# ─────────────────────────────── routes ──────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    try:
        spec = spec_from_form()
        proposals = generate_proposals(spec)
    except ValueError as e:
        return render_template("index.html", error=str(e)), 400

    run_id = uuid.uuid4().hex[:12]
    run_dir = os.path.join(OUT_ROOT, run_id)
    os.makedirs(run_dir, exist_ok=True)
    base = _slug(spec.project_name)

    results = []
    for prop in proposals:
        pdf_name = f"{base}_protasi_{prop.index}.pdf"
        dxf_name = f"{base}_protasi_{prop.index}.dxf"
        write_proposal_pdf(prop, os.path.join(run_dir, pdf_name))
        write_proposal_dxf(prop, os.path.join(run_dir, dxf_name))

        previews = []
        if _HAS_PYMUPDF:
            try:
                doc = pymupdf.open(os.path.join(run_dir, pdf_name))
                for pi in range(min(len(prop.floors), doc.page_count)):
                    png = f"{base}_p{prop.index}_pg{pi}.png"
                    doc[pi].get_pixmap(dpi=110).save(os.path.join(run_dir, png))
                    previews.append(url_for("serve_file", run_id=run_id, filename=png))
                doc.close()
            except Exception:
                previews = []

        results.append({
            "index": prop.index,
            "title": prop.title,
            "floors": [{"label": fl.floor_label,
                        "gross": round(fl.footprint_area, 1),
                        "net": round(fl.net_area, 1)} for fl in prop.floors],
            "warnings": prop.warnings,
            "pdf": url_for("download_file", run_id=run_id, filename=pdf_name),
            "dxf": url_for("download_file", run_id=run_id, filename=dxf_name),
            "previews": previews,
        })

    all_name = f"{base}_ola.pdf"
    write_all_pdf(proposals, os.path.join(run_dir, all_name))
    all_pdf = url_for("download_file", run_id=run_id, filename=all_name)

    return render_template("results.html", spec=spec, results=results,
                           all_pdf=all_pdf, shape=("Πολυγωνικό (Γ)"
                           if spec.is_polygonal else "Ορθογώνιο"))


@app.route("/file/<run_id>/<path:filename>")
def serve_file(run_id: str, filename: str):
    """Εμφάνιση αρχείου inline (π.χ. προεπισκόπηση PNG)."""
    safe = os.path.join(OUT_ROOT, run_id)
    if not os.path.isdir(safe):
        abort(404)
    return send_from_directory(safe, filename)


@app.route("/download/<run_id>/<path:filename>")
def download_file(run_id: str, filename: str):
    """Λήψη αρχείου (PDF/DXF) ως attachment."""
    safe = os.path.join(OUT_ROOT, run_id)
    if not os.path.isdir(safe):
        abort(404)
    return send_from_directory(safe, filename, as_attachment=True)


if __name__ == "__main__":
    # HOST=0.0.0.0 ώστε να λειτουργεί και σε cloud (Codespaces/Replit/Render).
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    print(f"\n  ▶ Γεννήτρια κατόψεων — τοπικά: http://127.0.0.1:{port}\n")
    app.run(host=host, port=port, debug=False)

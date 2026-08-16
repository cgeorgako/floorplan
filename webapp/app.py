"""Flask web διεπαφή για τη γεννήτρια προτάσεων κατόψεων κατοικίας.

Ροή: φόρμα HTML → συλλογή δεδομένων → εκτέλεση της Python γεννήτριας →
παραγωγή PDF (σε κλίμακα) + DXF (R12) → σελίδα αποτελεσμάτων με προεπισκόπηση
και συνδέσμους λήψης.

Τα παραγόμενα αρχεία αποθηκεύονται στο Replit Object Storage ώστε να επιβιώνουν
επανεκκινήσεις του container.  Κατά την εξυπηρέτηση, ελέγχεται πρώτα η τοπική
προσωρινή μνήμη (webapp/static/out/) και αν λείπει το αρχείο κατεβαίνει αυτόματα
από το Object Storage.

Εκτέλεση:
    python -m webapp.app         (ή)   python webapp/app.py
    → άνοιξε http://127.0.0.1:5000
"""
from __future__ import annotations

import logging
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

# ── Replit Object Storage (persistent across restarts) ──────────────────────
try:
    from replit.object_storage import Client as _ObjClient
    _storage = _ObjClient()
    _HAS_OBJECT_STORAGE = True
except Exception:                        # pragma: no cover
    _storage = None
    _HAS_OBJECT_STORAGE = False

_log = logging.getLogger(__name__)


def _storage_key(run_id: str, filename: str) -> str:
    """Κλειδί αντικειμένου στο Object Storage."""
    return f"out/{run_id}/{filename}"


def _upload_to_storage(local_path: str, run_id: str, filename: str) -> None:
    """Ανεβάζει ένα τοπικό αρχείο στο Object Storage (αθόρυβα αν αποτύχει)."""
    if not _HAS_OBJECT_STORAGE:
        return
    try:
        with open(local_path, "rb") as fh:
            _storage.upload_from_bytes(
                _storage_key(run_id, filename), fh.read()
            )
    except Exception as exc:             # pragma: no cover
        _log.warning("Object Storage upload failed for %s/%s: %s",
                     run_id, filename, exc)


def _ensure_local(run_id: str, filename: str) -> bool:
    """Εξασφαλίζει ότι υπάρχει τοπικό αντίγραφο (κατεβάζει αν χρειαστεί).

    Επιστρέφει True αν το αρχείο είναι διαθέσιμο τοπικά.
    """
    run_dir = os.path.join(OUT_ROOT, run_id)
    local_path = os.path.join(run_dir, filename)

    if os.path.isfile(local_path):
        return True

    if not _HAS_OBJECT_STORAGE:
        return False

    try:
        data = _storage.download_as_bytes(_storage_key(run_id, filename))
        os.makedirs(run_dir, exist_ok=True)
        with open(local_path, "wb") as fh:
            fh.write(data)
        return True
    except Exception as exc:
        _log.warning("Object Storage download failed for %s/%s: %s",
                     run_id, filename, exc)
        return False


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
        has_hall=_b("has_hall"),
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
        _upload_to_storage(os.path.join(run_dir, pdf_name), run_id, pdf_name)
        _upload_to_storage(os.path.join(run_dir, dxf_name), run_id, dxf_name)

        # One preview entry per floor (PDF page index matches floor index).
        # Client-side PDF.js renders the correct page without any native dep.
        previews = [
            {
                "pdf_url": url_for("serve_file", run_id=run_id, filename=pdf_name),
                "page": pi,   # 0-based page index within the PDF
                "label": fl.floor_label,
            }
            for pi, fl in enumerate(prop.floors)
        ]

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
    _upload_to_storage(os.path.join(run_dir, all_name), run_id, all_name)
    all_pdf = url_for("download_file", run_id=run_id, filename=all_name)

    return render_template("results.html", spec=spec, results=results,
                           all_pdf=all_pdf, shape=("Πολυγωνικό (Γ)"
                           if spec.is_polygonal else "Ορθογώνιο"))


@app.route("/file/<run_id>/<path:filename>")
def serve_file(run_id: str, filename: str):
    """Εμφάνιση αρχείου inline (π.χ. προεπισκόπηση PNG).

    Αν το αρχείο δεν υπάρχει τοπικά (π.χ. μετά επανεκκίνηση), το κατεβάζει
    αυτόματα από το Object Storage πριν το σερβίρει.
    """
    if not _ensure_local(run_id, filename):
        abort(404)
    return send_from_directory(os.path.join(OUT_ROOT, run_id), filename)


@app.route("/download/<run_id>/<path:filename>")
def download_file(run_id: str, filename: str):
    """Λήψη αρχείου (PDF/DXF) ως attachment.

    Αν το αρχείο δεν υπάρχει τοπικά (π.χ. μετά επανεκκίνηση), το κατεβάζει
    αυτόματα από το Object Storage πριν το σερβίρει.
    """
    if not _ensure_local(run_id, filename):
        abort(404)
    return send_from_directory(os.path.join(OUT_ROOT, run_id), filename,
                               as_attachment=True)


if __name__ == "__main__":
    # HOST=0.0.0.0 ώστε να λειτουργεί και σε cloud (Codespaces/Replit/Render).
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    print(f"\n  ▶ Γεννήτρια κατόψεων — τοπικά: http://127.0.0.1:{port}\n")
    app.run(host=host, port=port, debug=False)

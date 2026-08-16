"""floorplan_gen — Γεννήτρια προτάσεων κατόψεων κατοικίας.

Τεχνικό Γραφείο Μελετών — Γεωργακόπουλος Χρήστος / Φουντάς Αθανάσιος.
Παράγει σχηματικές προτάσεις κατόψεων (PDF σε κλίμακα + DXF R12) βάσει των
βασικών αρχών σχεδιασμού του instructions.md.
"""
from .models import BuildingSpec, Orientation, Category, Proposal, FloorPlan
from .layout import generate_proposals
from .generator import run

__all__ = [
    "BuildingSpec", "Orientation", "Category", "Proposal", "FloorPlan",
    "generate_proposals", "run",
]
__version__ = "1.0.0"

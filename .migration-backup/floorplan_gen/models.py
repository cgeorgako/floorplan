"""Δομές δεδομένων για τη γεννήτρια κατόψεων κατοικίας.

Σύστημα συντεταγμένων (πάντα): άξονας X προς Ανατολή, άξονας Y προς Βορρά.
Ο Βορράς είναι πάντα στο επάνω μέρος του σχεδίου (+Y). Μονάδες: μέτρα (m).
Όλες οι διαστάσεις χώρων αποθηκεύονται ως *καθαρές εσωτερικές* (clear).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class Orientation(str, Enum):
    """Προσανατολισμός (ο Βορράς πάντα πάνω)."""
    N = "N"   # Βορράς
    S = "S"   # Νότος
    E = "E"   # Ανατολή
    W = "W"   # Δύση

    @property
    def gr(self) -> str:
        return {"N": "Βορράς", "S": "Νότος", "E": "Ανατολή", "W": "Δύση"}[self.value]

    @classmethod
    def parse(cls, s: str) -> "Orientation":
        s = (s or "").strip().upper()
        table = {
            "N": cls.N, "B": cls.N, "ΒΟΡΡΑΣ": cls.N, "ΒΟΡΕΙΑ": cls.N, "NORTH": cls.N,
            "S": cls.S, "Ν": cls.S, "ΝΟΤΟΣ": cls.S, "ΝΟΤΙΑ": cls.S, "SOUTH": cls.S,
            "E": cls.E, "Α": cls.E, "ΑΝΑΤΟΛΗ": cls.E, "ΑΝΑΤΟΛΙΚΑ": cls.E, "EAST": cls.E,
            "W": cls.W, "Δ": cls.W, "ΔΥΣΗ": cls.W, "ΔΥΤΙΚΑ": cls.W, "WEST": cls.W,
        }
        if s not in table:
            raise ValueError(f"Άγνωστος προσανατολισμός: {s!r} (δώσε N/S/E/W ή Β/Ν/Α/Δ)")
        return table[s]


class Category(str, Enum):
    """Κατηγορία χώρου — καθορίζει χρήση (κύρια/βοηθητική), ανάγκη φωτισμού, ζώνη."""
    LIVING = "living"        # Καθιστικό / διημέρευση
    SALON = "salon"          # Σαλόνι (επίσημο)
    KITCHEN = "kitchen"      # Κουζίνα
    BEDROOM_MASTER = "bedroom_master"
    BEDROOM = "bedroom"
    BATH = "bath"            # Λουτρό
    WC = "wc"               # WC
    STORAGE = "storage"      # Αποθήκη
    WARDROBE = "wardrobe"    # Βεστιάριο / ιματιοθήκη
    HALL = "hall"            # Χώρος εισόδου (hall)
    CORRIDOR = "corridor"    # Διάδρομος
    STAIRS = "stairs"        # Κλιμακοστάσιο

    @property
    def gr(self) -> str:
        return {
            "living": "Καθιστικό",
            "salon": "Σαλόνι",
            "kitchen": "Κουζίνα",
            "bedroom_master": "Κύριο Υπνοδωμάτιο",
            "bedroom": "Υπνοδωμάτιο",
            "bath": "Λουτρό",
            "wc": "WC",
            "storage": "Αποθήκη",
            "wardrobe": "Βεστιάριο",
            "hall": "Χωλ / Υποδοχή",
            "corridor": "Διάδρομος",
            "stairs": "Κλιμακοστάσιο",
        }[self.value]

    @property
    def is_main_use(self) -> bool:
        """Χώρος κύριας χρήσης (Κ.Κ. άρθρο 20 §2): απαιτεί άμεσο φυσικό φωτισμό."""
        return self in {
            Category.LIVING, Category.SALON, Category.KITCHEN,
            Category.BEDROOM_MASTER, Category.BEDROOM,
        }


# Προτίμηση ζώνης προσανατολισμού ανά κατηγορία (βιοκλιματικός σχεδιασμός,
# instructions.md §5.3). 'S' = νότια, 'N' = βόρεια ζώνη ανάσχεσης, κ.λπ.
ZONE_PREFERENCE = {
    Category.LIVING: "S",
    Category.SALON: "S",
    Category.KITCHEN: "E",
    Category.BEDROOM_MASTER: "S",
    Category.BEDROOM: "E",
    Category.BATH: "N",
    Category.WC: "N",
    Category.STORAGE: "N",
    Category.WARDROBE: "N",
    Category.HALL: "N",
    Category.CORRIDOR: "C",
    Category.STAIRS: "N",
}


@dataclass
class BuildingSpec:
    """Το σύνολο των δεδομένων εισόδου που ζητά ο χρήστης."""
    # Μέγιστο ορθογώνιο περίγραμμα (εξωτερικές διαστάσεις, m)
    max_width_ew: float          # μέγιστη διάσταση κατά Ανατολή–Δύση (X)
    max_length_ns: float         # μέγιστη διάσταση κατά Βορρά–Νότο (Y)

    entrance: Orientation        # προσανατολισμός κύριας εισόδου
    floors: int                  # 1 (ισόγειο) ή 2 (διώροφο)

    ext_wall: float              # πάχος εξωτερικής τοιχοποιίας (m)
    int_wall: float              # πάχος εσωτερικής τοιχοποιίας (m)

    bedrooms: int                # πλήθος υπνοδωματίων
    baths: int                   # πλήθος λουτρών
    wcs: int                     # πλήθος WC

    has_storage: bool            # οικιακή αποθήκη
    has_wardrobe: bool           # χώρος βεστιαρίου
    has_living: bool             # καθιστικό
    has_salon: bool              # σαλόνι
    has_big_kitchen: bool        # μεγάλη κουζίνα

    min_bedroom_side: float      # ελάχιστη πλευρά υπνοδωματίου (m), π.χ. 3.00
    max_total_area: float        # μέγιστο εμβαδόν ΜΕ τοίχους (m²)

    num_proposals: int           # πλήθος προτάσεων-λύσεων

    # Σχήμα εξωτερικού περιγράμματος: "polygonal" (Γ/L — προεπιλογή) ή
    # "rectangular" (ορθογώνιο, μόνο αν ζητηθεί ρητά). Πάντα ορθογωνισμένο,
    # χωρίς καμπύλες.
    footprint_shape: str = "polygonal"

    # Προαιρετικές παράμετροι με λογικές προεπιλογές
    project_name: str = "Κατοικία"
    client: str = ""
    location: str = "Αμαλιάδα, Π.Ε. Ηλείας"

    @property
    def is_polygonal(self) -> bool:
        return str(self.footprint_shape).strip().lower() not in (
            "rectangular", "rect", "ορθογώνιο", "ορθογωνικό", "orthogonal")

    def validate(self) -> List[str]:
        errs: List[str] = []
        if self.max_width_ew <= 0 or self.max_length_ns <= 0:
            errs.append("Οι διαστάσεις του περιγράμματος πρέπει να είναι θετικές.")
        if self.floors not in (1, 2):
            errs.append("Οι όροφοι πρέπει να είναι 1 (ισόγειο) ή 2 (διώροφο).")
        if self.ext_wall <= 0 or self.int_wall <= 0:
            errs.append("Τα πάχη τοιχοποιίας πρέπει να είναι θετικά.")
        if self.bedrooms < 1:
            errs.append("Απαιτείται τουλάχιστον 1 υπνοδωμάτιο.")
        if self.num_proposals < 1:
            errs.append("Το πλήθος προτάσεων πρέπει να είναι ≥ 1.")
        if self.max_total_area <= 0:
            errs.append("Το μέγιστο εμβαδόν πρέπει να είναι θετικό.")
        env = self.max_width_ew * self.max_length_ns
        if self.max_total_area > env + 1e-6:
            # Δεν είναι σφάλμα: το εμβαδόν κόβεται από το περίγραμμα, απλή ενημέρωση.
            pass
        return errs


@dataclass
class Opening:
    """Άνοιγμα (θύρα/παράθυρο) πάνω σε πλευρά χώρου."""
    kind: str                    # "door" | "window"
    side: str                    # "N" | "S" | "E" | "W" (πλευρά του χώρου)
    offset: float                # απόσταση αρχής ανοίγματος από τη γωνία (m)
    width: float                 # καθαρό πλάτος ανοίγματος (m)
    to_exterior: bool = False    # True αν δίνει στο εξωτερικό (παράθυρο/πόρτα εισόδου)


@dataclass
class Room:
    """Χώρος με καθαρό (εσωτερικό) ορθογώνιο x0..x1, y0..y1 σε m."""
    category: Category
    name: str
    x0: float
    y0: float
    x1: float
    y1: float
    openings: List[Opening] = field(default_factory=list)
    # Πλευρές του χώρου που εφάπτονται στο εξωτερικό περίβλημα ('N','S','E','W').
    # Ορίζονται κατά την τοποθέτηση (γενικό για πολυγωνικά περιγράμματα).
    ext_sides: set = field(default_factory=set)

    @property
    def w(self) -> float:      # καθαρό πλάτος (κατά X, Α–Δ)
        return self.x1 - self.x0

    @property
    def d(self) -> float:      # καθαρό βάθος (κατά Y, Β–Ν)
        return self.y1 - self.y0

    @property
    def area(self) -> float:   # καθαρό εμβαδόν
        return self.w * self.d

    @property
    def cx(self) -> float:
        return 0.5 * (self.x0 + self.x1)

    @property
    def cy(self) -> float:
        return 0.5 * (self.y0 + self.y1)


@dataclass
class FloorPlan:
    """Μία κάτοψη ορόφου."""
    floor_label: str             # π.χ. "Ισόγειο", "Α' Όροφος"
    width_ew: float              # πλάτος περιβάλλοντος ορθογωνίου (X, m)
    length_ns: float             # μήκος περιβάλλοντος ορθογωνίου (Y, m)
    ext_wall: float
    int_wall: float
    rooms: List[Room] = field(default_factory=list)
    entrance: Optional[Orientation] = None
    # Εξωτερικό περίγραμμα ως ορθογωνισμένο πολύγωνο (λίστα κορυφών, CCW).
    outline: List[Tuple[float, float]] = field(default_factory=list)
    # Ορθογώνια «κύτταρα» που συνθέτουν το περίγραμμα (για σχεδίαση τοίχων).
    cells: List[Tuple[float, float, float, float]] = field(default_factory=list)

    @property
    def footprint_area(self) -> float:
        """Μικτό εμβαδόν με τοίχους (εμβαδόν πολυγώνου περιγράμματος)."""
        if len(self.outline) >= 3:
            s = 0.0
            n = len(self.outline)
            for i in range(n):
                x0, y0 = self.outline[i]
                x1, y1 = self.outline[(i + 1) % n]
                s += x0 * y1 - x1 * y0
            return abs(s) / 2.0
        return self.width_ew * self.length_ns

    @property
    def net_area(self) -> float:
        return sum(r.area for r in self.rooms)


@dataclass
class Proposal:
    """Μία πρόταση-λύση: μπορεί να έχει 1 (ισόγειο) ή 2 (διώροφο) κατόψεις."""
    index: int
    spec: BuildingSpec
    floors: List[FloorPlan] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    seed: int = 0

    @property
    def title(self) -> str:
        return f"Πρόταση {self.index}"

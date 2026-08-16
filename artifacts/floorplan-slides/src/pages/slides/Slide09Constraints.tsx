export default function Slide09Constraints() {
  const items = [
    {
      label: "Σχηματική Μελέτη",
      body: "Τα αρχεία αποτελούν σχηματική προμελέτη — ΔΕΝ υποκαθιστούν οριστική αρχιτεκτονική μελέτη ή μελέτη έκδοσης άδειας.",
    },
    {
      label: "Πολεοδομικοί Κανονισμοί",
      body: "Η εφαρμογή ελέγχει εσωτερικές απαιτήσεις (φωτισμός, αερισμός, ελάχ. διαστάσεις) αλλά δεν αντικαθιστά τον έλεγχο πολεοδομικών όρων του οικοπέδου.",
    },
    {
      label: "Δομική & Μηχ/κή Μελέτη",
      body: "Η κάτοψη δεν λαμβάνει υπόψη φέροντα οργανισμό, τεχνικές υποδομές (Η/Μ) ή γεωτεχνικές συνθήκες.",
    },
    {
      label: "Αριθμός Προτάσεων",
      body: "Η τρέχουσα έκδοση παράγει έως 3 παραλλαγές ανά εκτέλεση. Δεν υποστηρίζεται ακόμη πολυόροφο με διαφορετικούς χώρους ανά όροφο.",
    },
    {
      label: "Μορφολογία",
      body: "Υποστηρίζονται ορθογωνικό και Γ-σχήμα. Άλλες ακανόνιστες μορφολογίες (Τ, Λ κ.λπ.) δεν παράγονται αυτόματα.",
    },
  ];

  return (
    <div className="relative w-screen h-screen overflow-hidden" style={{ background: "#FAFAFA" }}>
      {/* Header */}
      <div
        className="absolute top-0 left-0"
        style={{ paddingTop: "7vh", paddingLeft: "6vw" }}
      >
        <div className="border-t border-black mb-[2vh]" style={{ borderTopWidth: "1.5px", width: "3vw" }} />
        <h2
          className="font-black uppercase tracking-widest text-black"
          style={{ fontFamily: "'Inter', sans-serif", fontSize: "2.4vw", letterSpacing: "0.13em" }}
        >
          Περιορισμοί &amp; Σημειώσεις
        </h2>
        <p
          style={{ fontFamily: "'Playfair Display', serif", fontSize: "1.55vw", fontStyle: "italic", color: "#666666", marginTop: "1.2vh" }}
        >
          Τι δεν καλύπτει η παρούσα έκδοση
        </p>
      </div>

      {/* Items */}
      <div
        className="absolute inset-x-0"
        style={{ top: "25vh", bottom: "12vh", paddingLeft: "6vw", paddingRight: "6vw" }}
      >
        {items.map((item, i) => (
          <div
            key={i}
            className="flex items-start"
            style={{ borderBottom: "1px solid #E8E8E8", paddingTop: "1.8vh", paddingBottom: "1.8vh" }}
          >
            <span
              className="font-black shrink-0"
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.5vw", color: "#000000", minWidth: "24vw" }}
            >
              {item.label}
            </span>
            <span
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.45vw", color: "#555555", lineHeight: 1.55 }}
            >
              {item.body}
            </span>
          </div>
        ))}
        <div className="border-t" style={{ borderColor: "#E8E8E8" }} />
      </div>

      {/* Footer */}
      <div
        className="absolute bottom-0 inset-x-0 flex items-center justify-between"
        style={{ paddingLeft: "6vw", paddingRight: "6vw", paddingBottom: "2.4vh" }}
      >
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999", letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Γεωργακόπουλος / Φουντάς
        </span>
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999" }}>09</span>
      </div>
    </div>
  );
}

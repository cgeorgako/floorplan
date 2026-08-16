export default function Slide04Inputs() {
  const params = [
    ["Διαστάσεις οικοπέδου", "Μέγιστο πλάτος Α-Δ & βάθος Β-Ν (m)"],
    ["Αριθμός ορόφων", "Ισόγειο, 1 ή 2 όροφοι"],
    ["Μορφολογία κτιρίου", "Ορθογωνικό ή Πολυγωνικό (Γ-σχήμα)"],
    ["Κατεύθυνση εισόδου", "Β, Ν, Α ή Δ"],
    ["Υπνοδωμάτια & λουτρά", "Αριθμός, Master bedroom, ντουλάπα"],
    ["Χώροι ημέρας", "Σαλόνι, τραπεζαρία / καθιστικό, κουζίνα"],
    ["Βοηθητικοί χώροι", "Αποθήκη, WC, κλιμακοστάσιο"],
    ["Στοιχεία κτιρίου", "Πάχος τοίχων (εξωτ. / εσωτ.), ελάχ. πλευρά υ/δ"],
    ["Μέγ. συνολικό εμβαδόν", "Μέγιστη επιτρεπόμενη δόμηση (m²)"],
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
          Παράμετροι Εισόδου
        </h2>
        <p
          style={{ fontFamily: "'Playfair Display', serif", fontSize: "1.55vw", fontStyle: "italic", color: "#666666", marginTop: "1.2vh" }}
        >
          Τα στοιχεία που συμπληρώνει ο μελετητής στη φόρμα
        </p>
      </div>

      {/* Parameter table */}
      <div
        className="absolute inset-x-0"
        style={{ top: "24vh", bottom: "12vh", paddingLeft: "6vw", paddingRight: "6vw" }}
      >
        {/* Column headers */}
        <div
          className="flex mb-[1.2vh]"
          style={{ borderBottom: "2px solid #000000", paddingBottom: "1vh" }}
        >
          <span
            className="font-black uppercase tracking-widest"
            style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.15vw", color: "#000000", letterSpacing: "0.14em", width: "38%" }}
          >
            Παράμετρος
          </span>
          <span
            className="font-black uppercase tracking-widest"
            style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.15vw", color: "#000000", letterSpacing: "0.14em" }}
          >
            Περιγραφή
          </span>
        </div>

        {/* Rows */}
        {params.map(([label, desc], i) => (
          <div
            key={i}
            className="flex items-baseline"
            style={{ borderBottom: "1px solid #E8E8E8", paddingTop: "1.25vh", paddingBottom: "1.25vh" }}
          >
            <span
              className="font-semibold"
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.5vw", color: "#000000", width: "38%", flexShrink: 0 }}
            >
              {label}
            </span>
            <span
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.45vw", color: "#555555" }}
            >
              {desc}
            </span>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div
        className="absolute bottom-0 inset-x-0 flex items-center justify-between"
        style={{ paddingLeft: "6vw", paddingRight: "6vw", paddingBottom: "2.4vh" }}
      >
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999", letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Γεωργακόπουλος / Φουντάς
        </span>
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999" }}>04</span>
      </div>
    </div>
  );
}

export default function Slide07Outputs() {
  const files = [
    {
      ext: "PDF",
      title: "Κάτοψη σε Κλίμακα",
      items: [
        "Κλίμακα 1:50 / 1:100 κ.λπ.",
        "Εξωτερικές & αλυσιδωτές διαστάσεις",
        "Βέλος βορρά + γραμμική κλίμακα",
        "Πίνακας χώρων (καθαρά / μικτά m²)",
        "Έλεγχος φωτισμού & αερισμού",
        "Υπόμνημα χρωμάτων ανά χρήση",
      ],
    },
    {
      ext: "DXF",
      title: "Αρχείο CAD",
      items: [
        "Μορφή AutoCAD R12 (universal)",
        "Τοίχοι, χώροι, ανοίγματα σε layers",
        "Ετικέτες χώρων ως text entities",
        "Άμεση εισαγωγή σε AutoCAD, ZWCAD, LibreCAD",
        "Βάση για τελική αρχιτεκτονική μελέτη",
      ],
    },
    {
      ext: "ZIP",
      title: "Πλήρης Δέσμη",
      items: [
        "Όλα τα PDF + DXF όλων των προτάσεων",
        "Προεπισκόπηση PNG ανά κάτοψη",
        "Ενιαία λήψη με ένα κλικ",
        "Μόνιμη αποθήκευση στο cloud",
        "Πρόσβαση ανά πάσα στιγμή από τον φυλλομετρητή",
      ],
    },
  ];

  return (
    <div className="relative w-screen h-screen overflow-hidden" style={{ background: "#FAFAFA" }}>
      {/* Header */}
      <div
        className="absolute top-0 inset-x-0"
        style={{ paddingTop: "7vh", paddingLeft: "6vw" }}
      >
        <div className="border-t border-black mb-[2vh]" style={{ borderTopWidth: "1.5px", width: "3vw" }} />
        <h2
          className="font-black uppercase tracking-widest text-black"
          style={{ fontFamily: "'Inter', sans-serif", fontSize: "2.4vw", letterSpacing: "0.13em" }}
        >
          Αρχεία Εξόδου
        </h2>
        <p
          style={{ fontFamily: "'Playfair Display', serif", fontSize: "1.55vw", fontStyle: "italic", color: "#666666", marginTop: "1.2vh" }}
        >
          Τι παραδίδεται σε κάθε εκτέλεση
        </p>
      </div>

      {/* Three columns */}
      <div
        className="absolute inset-x-0 flex items-stretch"
        style={{ top: "26vh", bottom: "12vh", paddingLeft: "6vw", paddingRight: "6vw", gap: "3vw" }}
      >
        {files.map((f, i) => (
          <div key={i} className="flex-1 flex flex-col">
            {/* Top border */}
            <div style={{ height: "3px", background: i === 0 ? "#000000" : "#CCCCCC", marginBottom: "3vh" }} />

            {/* Extension badge */}
            <div style={{ marginBottom: "1.8vh" }}>
              <span
                className="inline-block font-black"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "2.8vw",
                  color: "#000000",
                  letterSpacing: "0.04em",
                }}
              >
                .{f.ext}
              </span>
            </div>

            <h3
              className="font-semibold text-black"
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.5vw", marginBottom: "2.5vh" }}
            >
              {f.title}
            </h3>

            {/* Items */}
            <div className="flex flex-col">
              {f.items.map((item, j) => (
                <div
                  key={j}
                  className="flex items-start"
                  style={{ borderBottom: "1px solid #EEEEEE", paddingTop: "1.1vh", paddingBottom: "1.1vh" }}
                >
                  <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.4vw", color: "#555555", lineHeight: 1.5 }}>
                    {item}
                  </span>
                </div>
              ))}
            </div>
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
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999" }}>07</span>
      </div>
    </div>
  );
}

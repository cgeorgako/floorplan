export default function Slide08Technologies() {
  const techs = [
    { name: "Python", role: "Αλγόριθμος διάταξης, κανονισμοί, γεωμετρία" },
    { name: "Flask", role: "Web server, φόρμα, δρομολόγηση αρχείων" },
    { name: "ReportLab", role: "Δημιουργία PDF σε κλίμακα με διαστάσεις" },
    { name: "ezdxf", role: "Εξαγωγή DXF (AutoCAD R12)" },
    { name: "Object Storage", role: "Μόνιμη αποθήκευση αρχείων στο cloud" },
    { name: "PDF.js", role: "Προεπισκόπηση PDF στον φυλλομετρητή" },
  ];

  return (
    <div className="relative w-screen h-screen overflow-hidden" style={{ background: "#FAFAFA" }}>
      {/* Left column — big stat + heading */}
      <div
        className="absolute inset-y-0 left-0 flex flex-col justify-center"
        style={{ width: "36vw", paddingLeft: "6vw", paddingRight: "3vw", background: "#F0EEEB" }}
      >
        <div className="border-t border-black mb-[2vh]" style={{ borderTopWidth: "1.5px", width: "3vw" }} />
        <h2
          className="font-black uppercase tracking-widest text-black leading-tight"
          style={{ fontFamily: "'Inter', sans-serif", fontSize: "2.5vw", letterSpacing: "0.12em" }}
        >
          Τεχνολογίες
        </h2>
        <p
          style={{ fontFamily: "'Playfair Display', serif", fontSize: "1.5vw", fontStyle: "italic", color: "#666666", marginTop: "2vh" }}
        >
          Open-source stack — χωρίς εξαρτήσεις SaaS
        </p>

        {/* Big stat */}
        <div style={{ marginTop: "5vh" }}>
          <span
            className="font-black text-black"
            style={{ fontFamily: "'Inter', sans-serif", fontSize: "9vw", lineHeight: 1, display: "block" }}
          >
            100%
          </span>
          <span
            className="font-semibold uppercase tracking-widest"
            style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#666666", letterSpacing: "0.14em" }}
          >
            Python backend
          </span>
        </div>

        <div style={{ marginTop: "3.5vh" }}>
          <span
            className="font-black text-black"
            style={{ fontFamily: "'Inter', sans-serif", fontSize: "9vw", lineHeight: 1, display: "block" }}
          >
            &lt;5s
          </span>
          <span
            className="font-semibold uppercase tracking-widest"
            style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#666666", letterSpacing: "0.14em" }}
          >
            Χρόνος εκτέλεσης
          </span>
        </div>
      </div>

      {/* Right column — tech list */}
      <div
        className="absolute inset-y-0 right-0 flex flex-col justify-center"
        style={{ left: "38vw", paddingLeft: "4vw", paddingRight: "5vw" }}
      >
        {techs.map((t, i) => (
          <div
            key={i}
            className="flex items-baseline"
            style={{ borderBottom: "1px solid #E8E8E8", paddingTop: "2.1vh", paddingBottom: "2.1vh" }}
          >
            <span
              className="font-black shrink-0"
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.6vw", color: "#000000", minWidth: "13vw" }}
            >
              {t.name}
            </span>
            <span
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.45vw", color: "#555555" }}
            >
              {t.role}
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
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999" }}>08</span>
      </div>
    </div>
  );
}

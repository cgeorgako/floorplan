const base = import.meta.env.BASE_URL;

export default function Slide02WhatIs() {
  return (
    <div className="relative w-screen h-screen overflow-hidden" style={{ background: "#FAFAFA" }}>
      {/* Left column — floor plan SVG */}
      <div
        className="absolute inset-y-0 left-0 flex items-center justify-center"
        style={{ width: "44vw", background: "#F2F0ED" }}
      >
        {/* Simple inline L-shaped floor plan diagram */}
        <svg
          viewBox="0 0 260 200"
          style={{ width: "32vw", height: "auto" }}
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* L-shape footprint fill */}
          <polygon
            points="20,180 240,180 240,100 170,100 170,20 20,20"
            fill="#E8E4DF"
            stroke="#000000"
            strokeWidth="2.5"
          />
          {/* Day zone label */}
          <rect x="20" y="100" width="220" height="80" fill="#DCE8F5" stroke="none" />
          <text x="130" y="147" textAnchor="middle" fontSize="11" fontFamily="Inter,sans-serif" fill="#444">Ζώνη Ημέρας</text>
          {/* Night zone label */}
          <rect x="20" y="20" width="150" height="80" fill="#DCF5E0" stroke="none" />
          <text x="95" y="67" textAnchor="middle" fontSize="11" fontFamily="Inter,sans-serif" fill="#444">Ζώνη Νύχτας</text>
          {/* Notch label */}
          <rect x="170" y="20" width="70" height="80" fill="#F2F0ED" stroke="none" />
          <text x="205" y="62" textAnchor="middle" fontSize="9" fontFamily="Inter,sans-serif" fill="#aaa">εσοχή</text>
          {/* Outline on top */}
          <polygon
            points="20,180 240,180 240,100 170,100 170,20 20,20"
            fill="none"
            stroke="#000000"
            strokeWidth="2.5"
          />
          {/* N arrow */}
          <line x1="248" y1="185" x2="248" y2="173" stroke="#333" strokeWidth="1.5" markerEnd="url(#arr)" />
          <text x="248" y="191" textAnchor="middle" fontSize="8" fontFamily="Inter,sans-serif" fill="#333">Ν</text>
          <defs>
            <marker id="arr" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
              <path d="M0,0 L0,6 L6,3 z" fill="#333" />
            </marker>
          </defs>
        </svg>
        <p
          className="absolute bottom-0 left-0 right-0 text-center"
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "1.15vw",
            color: "#999999",
            paddingBottom: "3vh",
            letterSpacing: "0.05em",
          }}
        >
          Παράδειγμα Γ-σχήματος (πολυγωνικό)
        </p>
      </div>

      {/* Right column — description */}
      <div
        className="absolute inset-y-0 right-0 flex flex-col justify-center"
        style={{ width: "52vw", paddingLeft: "5vw", paddingRight: "5vw" }}
      >
        <div className="w-8 border-t border-black mb-[2.5vh]" style={{ borderTopWidth: "1.5px" }} />
        <h2
          className="font-black uppercase tracking-widest text-black leading-tight mb-[3vh]"
          style={{ fontFamily: "'Inter', sans-serif", fontSize: "2.6vw", letterSpacing: "0.12em" }}
        >
          Τι είναι
        </h2>

        <p
          className="text-black leading-relaxed mb-[3.5vh]"
          style={{ fontFamily: "'Playfair Display', serif", fontSize: "1.7vw", fontStyle: "italic" }}
        >
          Διαδικτυακή εφαρμογή που παράγει αυτόματα σχηματικές προτάσεις κατόψεων μονοκατοικίας με βάση τα δεδομένα του έργου.
        </p>

        {/* Spec rows */}
        {[
          ["Εξαγωγή PDF", "Κάτοψη σε κλίμακα με πλήρη διαστάσεις"],
          ["Εξαγωγή DXF", "Αρχείο CAD (AutoCAD R12), έτοιμο για επεξεργασία"],
          ["Προεπισκόπηση PNG", "Ορατή απευθείας στον φυλλομετρητή"],
          ["Πολλαπλές Προτάσεις", "Έως 3 παραλλαγές ανά εκτέλεση"],
          ["Ορθογωνικό ή Γ-σχήμα", "Επιλογή μορφολογίας κτιρίου"],
        ].map(([label, desc], i) => (
          <div key={i} className="flex flex-col" style={{ marginBottom: "1.6vh" }}>
            <div className="w-full border-t" style={{ borderColor: "#DDDDDD" }} />
            <div className="flex items-baseline" style={{ paddingTop: "1.2vh" }}>
              <span
                className="font-semibold shrink-0"
                style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.5vw", color: "#000000", minWidth: "20vw" }}
              >
                {label}
              </span>
              <span
                style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.4vw", color: "#666666" }}
              >
                {desc}
              </span>
            </div>
          </div>
        ))}
        <div className="w-full border-t" style={{ borderColor: "#DDDDDD" }} />
      </div>

      {/* Footer */}
      <div
        className="absolute bottom-0 inset-x-0 flex items-center justify-between"
        style={{ paddingLeft: "5vw", paddingRight: "5vw", paddingBottom: "2.4vh" }}
      >
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999", letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Γεωργακόπουλος / Φουντάς
        </span>
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999" }}>02</span>
      </div>
    </div>
  );
}

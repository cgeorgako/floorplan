export default function Slide03Problem() {
  return (
    <div className="relative w-screen h-screen overflow-hidden" style={{ background: "#FAFAFA" }}>
      {/* Centered header */}
      <div
        className="absolute top-0 inset-x-0 flex flex-col items-center justify-center"
        style={{ paddingTop: "8vh" }}
      >
        <div className="border-t border-black mb-[2vh]" style={{ borderTopWidth: "1.5px", width: "3vw" }} />
        <h2
          className="font-black uppercase tracking-widest text-black text-center"
          style={{ fontFamily: "'Inter', sans-serif", fontSize: "2.2vw", letterSpacing: "0.14em" }}
        >
          Πρόβλημα &amp; Λύση
        </h2>
      </div>

      {/* Two large columns */}
      <div
        className="absolute inset-x-0 flex"
        style={{ top: "22vh", bottom: "12vh", paddingLeft: "5vw", paddingRight: "5vw", gap: "4vw" }}
      >
        {/* Problem column */}
        <div
          className="flex-1 flex flex-col"
          style={{ borderTop: "3px solid #CCCCCC", paddingTop: "3vh" }}
        >
          <p
            className="uppercase tracking-widest font-semibold mb-[2.5vh]"
            style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999", letterSpacing: "0.16em" }}
          >
            Μέχρι τώρα
          </p>
          <p
            className="leading-relaxed text-black"
            style={{ fontFamily: "'Playfair Display', serif", fontSize: "2vw", fontStyle: "italic" }}
          >
            "Η σύνταξη σχηματικής κάτοψης για προμελέτη απαιτεί ώρες σχεδιασμού σε CAD, ακόμα και για απλά ορθογωνικά κτίρια."
          </p>
          <div style={{ marginTop: "3.5vh" }}>
            {[
              "Χειρωνακτική εργασία σε CAD για κάθε πρόταση",
              "Επαναλαμβανόμενος υπολογισμός εμβαδών",
              "Δύσκολη σύγκριση εναλλακτικών διατάξεων",
              "Καθυστέρηση στη φάση προμελέτης",
            ].map((item, i) => (
              <div key={i} className="flex items-start" style={{ marginBottom: "1.6vh" }}>
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.5vw", color: "#AAAAAA", marginRight: "1.2vw", flexShrink: 0, marginTop: "0.15em" }}>
                  &mdash;
                </span>
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.5vw", color: "#444444" }}>
                  {item}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Divider */}
        <div className="self-stretch border-l" style={{ borderColor: "#EBEBEB" }} />

        {/* Solution column */}
        <div
          className="flex-1 flex flex-col"
          style={{ borderTop: "3px solid #000000", paddingTop: "3vh" }}
        >
          <p
            className="uppercase tracking-widest font-semibold mb-[2.5vh]"
            style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#000000", letterSpacing: "0.16em" }}
          >
            Με τη Γεννήτρια
          </p>
          <p
            className="leading-relaxed text-black"
            style={{ fontFamily: "'Playfair Display', serif", fontSize: "2vw", fontStyle: "italic" }}
          >
            "Η εφαρμογή παράγει σε δευτερόλεπτα πλήρεις σχηματικές κατόψεις σε κλίμακα, με PDF, DXF και έλεγχο κανονισμών."
          </p>
          <div style={{ marginTop: "3.5vh" }}>
            {[
              "Αυτόματη διάταξη χώρων σε ζώνες ημέρας / νύχτας",
              "Έλεγχος φωτισμού, αερισμού και ΚΚ",
              "Έως 3 παραλλαγές ανά εκτέλεση",
              "Άμεση λήψη PDF + DXF",
            ].map((item, i) => (
              <div key={i} className="flex items-start" style={{ marginBottom: "1.6vh" }}>
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.5vw", color: "#000000", marginRight: "1.2vw", flexShrink: 0, marginTop: "0.15em" }}>
                  +
                </span>
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.5vw", color: "#000000", fontWeight: 500 }}>
                  {item}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        className="absolute bottom-0 inset-x-0 flex items-center justify-between"
        style={{ paddingLeft: "5vw", paddingRight: "5vw", paddingBottom: "2.4vh" }}
      >
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999", letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Γεωργακόπουλος / Φουντάς
        </span>
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999" }}>03</span>
      </div>
    </div>
  );
}

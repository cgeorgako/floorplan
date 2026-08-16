export default function Slide06Rules() {
  const rules = [
    {
      n: "01",
      title: "Βιοκλιματικός Προσανατολισμός",
      body: "Οι χώροι ημέρας τοποθετούνται στη νότια ζώνη για μέγιστη ηλιακή έκθεση. Οι χώροι νύχτας παραμένουν στη βόρεια ζώνη.",
    },
    {
      n: "02",
      title: "Ζωνοποίηση Χώρων",
      body: "Ζώνη ημέρας (σαλόνι, τραπεζαρία, κουζίνα), ζώνη υπηρεσιών (WC, λουτρό, αποθήκη, διάδρομος), ζώνη νύχτας (υπνοδωμάτια).",
    },
    {
      n: "03",
      title: "Ελάχιστες Διαστάσεις",
      body: "Κάθε υπνοδωμάτιο πληροί ελάχιστη πλευρά (τυπικά 3,00 m για master, 2,70 m για λοιπά) βάσει ΓΟΚ.",
    },
    {
      n: "04",
      title: "Φωτισμός & Αερισμός",
      body: "Αυτόματος έλεγχος κανονισμού: το άθροισμα ανοιγμάτων κάθε χώρου ελέγχεται έναντι ελαχίστου κ.κ. φωτ./αερ. (1/8 εμβαδού).",
    },
    {
      n: "05",
      title: "Κάλυψη & Δόμηση",
      body: "Ο αλγόριθμος σέβεται το μέγιστο συνολικό εμβαδόν που ορίζει ο μελετητής. Εφαρμόζεται αναλογική κλιμάκωση αν το εμβαδόν υπερβαίνεται.",
    },
  ];

  return (
    <div className="relative w-screen h-screen overflow-hidden" style={{ background: "#FAFAFA" }}>
      {/* Left header bar */}
      <div
        className="absolute top-0 left-0 bottom-0"
        style={{ width: "26vw", background: "#F0EEEB", display: "flex", flexDirection: "column", justifyContent: "center", paddingLeft: "5vw", paddingRight: "3vw" }}
      >
        <div className="border-t border-black mb-[2.5vh]" style={{ borderTopWidth: "1.5px", width: "3vw" }} />
        <h2
          className="font-black uppercase text-black leading-tight"
          style={{ fontFamily: "'Inter', sans-serif", fontSize: "2.5vw", letterSpacing: "0.1em" }}
        >
          Κανόνες Σχεδιασμού
        </h2>
        <p
          style={{ fontFamily: "'Playfair Display', serif", fontSize: "1.5vw", fontStyle: "italic", color: "#666666", marginTop: "2vh" }}
        >
          Αρχές που διέπουν τη διάταξη κάθε κατόψεως
        </p>
      </div>

      {/* Rules list — right */}
      <div
        className="absolute inset-y-0 right-0 flex flex-col justify-center"
        style={{ left: "28vw", paddingLeft: "3vw", paddingRight: "5vw", paddingTop: "5vh", paddingBottom: "10vh", gap: 0 }}
      >
        {rules.map((r, i) => (
          <div
            key={i}
            className="flex items-start"
            style={{ borderBottom: "1px solid #E8E8E8", paddingTop: "1.7vh", paddingBottom: "1.7vh" }}
          >
            <span
              className="font-black shrink-0"
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.2vw", color: "#CCCCCC", marginRight: "1.8vw", letterSpacing: "0.05em", paddingTop: "0.2em" }}
            >
              {r.n}
            </span>
            <div>
              <p
                className="font-semibold text-black"
                style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.5vw", marginBottom: "0.5vh" }}
              >
                {r.title}
              </p>
              <p
                style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.4vw", color: "#555555", lineHeight: 1.55 }}
              >
                {r.body}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div
        className="absolute bottom-0 inset-x-0 flex items-center justify-between"
        style={{ paddingLeft: "5vw", paddingRight: "5vw", paddingBottom: "2.4vh" }}
      >
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999", letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Γεωργακόπουλος / Φουντάς
        </span>
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999" }}>06</span>
      </div>
    </div>
  );
}

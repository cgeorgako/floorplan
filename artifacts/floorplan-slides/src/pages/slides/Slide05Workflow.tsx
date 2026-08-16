export default function Slide05Workflow() {
  const steps = [
    {
      num: "01",
      title: "Φόρμα",
      desc: "Ο μελετητής συμπληρώνει τα στοιχεία του έργου — διαστάσεις, χώρους, προσανατολισμό.",
      detail: "Flask web interface",
    },
    {
      num: "02",
      title: "Γεννήτρια",
      desc: "Ο αλγόριθμος διατάσσει τους χώρους σε ζώνες, ελέγχει κανονισμούς και υπολογίζει εμβαδά.",
      detail: "Python layout engine",
    },
    {
      num: "03",
      title: "Εξαγωγή",
      desc: "Παραδίδονται PDF κλίμακας, DXF για CAD και προεπισκόπηση PNG ανά πρόταση.",
      detail: "ReportLab + ezdxf",
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
          Ροή Εργασίας
        </h2>
        <p
          style={{ fontFamily: "'Playfair Display', serif", fontSize: "1.55vw", fontStyle: "italic", color: "#666666", marginTop: "1.2vh" }}
        >
          Από τη φόρμα στην κάτοψη σε δευτερόλεπτα
        </p>
      </div>

      {/* Three step columns */}
      <div
        className="absolute inset-x-0 flex items-stretch"
        style={{ top: "26vh", bottom: "14vh", paddingLeft: "6vw", paddingRight: "6vw", gap: "2vw" }}
      >
        {steps.map((step, i) => (
          <div key={i} className="flex-1 flex flex-col" style={{ position: "relative" }}>
            {/* Top border — thick */}
            <div style={{ height: "3px", background: i === 1 ? "#000000" : "#CCCCCC", marginBottom: "3vh" }} />

            {/* Step number */}
            <span
              className="font-black"
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "5vw",
                color: "#F0EEEC",
                lineHeight: 1,
                marginBottom: "1.5vh",
              }}
            >
              {step.num}
            </span>

            {/* Title */}
            <h3
              className="font-black uppercase tracking-widest text-black"
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "2vw", letterSpacing: "0.12em", marginBottom: "2.5vh" }}
            >
              {step.title}
            </h3>

            {/* Description */}
            <p
              className="text-black leading-relaxed"
              style={{ fontFamily: "'Playfair Display', serif", fontSize: "1.6vw", fontStyle: "italic", color: "#444444" }}
            >
              {step.desc}
            </p>

            {/* Tech tag */}
            <div style={{ marginTop: "auto" }}>
              <span
                className="inline-block"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: "1.2vw",
                  color: "#999999",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  borderTop: "1px solid #DDDDDD",
                  paddingTop: "1.4vh",
                }}
              >
                {step.detail}
              </span>
            </div>

            {/* Connector arrow (not after last) */}
            {i < steps.length - 1 && (
              <div
                className="absolute right-0 top-1/2 flex items-center justify-center"
                style={{ transform: "translate(1vw, -50%)", zIndex: 10 }}
              >
                <svg width="2vw" height="2vw" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="#BBBBBB" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            )}
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
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "#999999" }}>05</span>
      </div>
    </div>
  );
}

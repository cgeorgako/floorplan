const base = import.meta.env.BASE_URL;

export default function Slide01Title() {
  return (
    <div className="relative w-screen h-screen overflow-hidden bg-white">
      {/* Hero photo top 58% */}
      <div className="absolute inset-x-0 top-0" style={{ height: "58vh" }}>
        <img
          src={`${base}hero.jpg`}
          crossOrigin="anonymous"
          alt="Αρχιτεκτονική κάτοψη"
          className="w-full h-full object-cover"
        />
        {/* subtle dark gradient at bottom of photo */}
        <div
          className="absolute inset-x-0 bottom-0"
          style={{
            height: "30%",
            background: "linear-gradient(to bottom, transparent, rgba(0,0,0,0.18))",
          }}
        />
      </div>

      {/* White content area bottom 42% */}
      <div
        className="absolute inset-x-0 bottom-0 flex flex-col justify-center"
        style={{ height: "42vh", paddingLeft: "5vw", paddingRight: "5vw" }}
      >
        {/* thin rule */}
        <div className="w-12 border-t border-black mb-[2.2vh]" style={{ borderTopWidth: "1.5px" }} />

        <h1
          className="font-black uppercase tracking-widest leading-none text-black"
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "3.8vw",
            letterSpacing: "0.14em",
            textWrap: "balance",
          }}
        >
          Γεννήτρια Κατόψεων
        </h1>

        <p
          className="mt-[1.4vh] text-black"
          style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: "1.9vw",
            fontStyle: "italic",
            fontWeight: 400,
          }}
        >
          Αυτόματες σχηματικές προτάσεις κατόψεων μονοκατοικίας
        </p>

        {/* Footer row */}
        <div
          className="absolute bottom-0 inset-x-0 flex items-center justify-between"
          style={{ paddingLeft: "5vw", paddingRight: "5vw", paddingBottom: "2.4vh" }}
        >
          <span
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "1.4vw",
              color: "#999999",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Γεωργακόπουλος Χρ. / Φουντάς Αθ. &mdash; Αμαλιάδα
          </span>
          <span
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "1.4vw",
              color: "#999999",
            }}
          >
            01
          </span>
        </div>
      </div>
    </div>
  );
}

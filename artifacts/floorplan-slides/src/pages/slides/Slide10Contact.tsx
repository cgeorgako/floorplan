const base = import.meta.env.BASE_URL;

export default function Slide10Contact() {
  return (
    <div className="relative w-screen h-screen overflow-hidden">
      {/* Full background image with overlay */}
      <img
        src={`${base}hero.jpg`}
        crossOrigin="anonymous"
        alt="Background"
        className="absolute inset-0 w-full h-full object-cover"
        style={{ filter: "grayscale(40%)" }}
      />
      <div
        className="absolute inset-0"
        style={{ background: "linear-gradient(135deg, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.55) 100%)" }}
      />

      {/* Content centered */}
      <div
        className="absolute inset-0 flex flex-col items-center justify-center text-white"
        style={{ paddingLeft: "10vw", paddingRight: "10vw" }}
      >
        <div
          className="border-t border-white mb-[3vh]"
          style={{ borderTopWidth: "1px", width: "4vw", opacity: 0.5 }}
        />

        <h2
          className="font-black uppercase text-white text-center leading-tight"
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: "4vw",
            letterSpacing: "0.14em",
            textWrap: "balance",
          }}
        >
          Επόμενα Βήματα
        </h2>

        <p
          className="text-center mt-[2.5vh]"
          style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: "1.9vw",
            fontStyle: "italic",
            color: "rgba(255,255,255,0.82)",
            maxWidth: "60vw",
            textWrap: "balance",
          }}
        >
          Η εφαρμογή είναι διαθέσιμη για δοκιμαστική χρήση. Καλούμε εταίρους να μας αποστείλουν σχόλια και δεδομένα παραδειγμάτων.
        </p>

        {/* Divider */}
        <div
          className="border-t mt-[4.5vh] mb-[4.5vh]"
          style={{ borderColor: "rgba(255,255,255,0.2)", width: "50vw" }}
        />

        {/* Contact block */}
        <div className="flex gap-[8vw] text-center">
          <div>
            <p
              className="uppercase tracking-widest font-semibold"
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.2vw", color: "rgba(255,255,255,0.5)", letterSpacing: "0.16em", marginBottom: "1.2vh" }}
            >
              Τεχνικό Γραφείο
            </p>
            <p
              className="font-black text-white"
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.6vw" }}
            >
              Γεωργακόπουλος Χρ. / Φουντάς Αθ.
            </p>
          </div>
          <div>
            <p
              className="uppercase tracking-widest font-semibold"
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.2vw", color: "rgba(255,255,255,0.5)", letterSpacing: "0.16em", marginBottom: "1.2vh" }}
            >
              Έδρα
            </p>
            <p
              className="font-black text-white"
              style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.6vw" }}
            >
              Αμαλιάδα, Ηλεία
            </p>
          </div>
        </div>

        <div
          className="mt-[5vh] border-t"
          style={{ borderColor: "rgba(255,255,255,0.15)", paddingTop: "2.5vh", width: "100%" }}
        >
          <p
            className="text-center uppercase tracking-widest"
            style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "rgba(255,255,255,0.35)", letterSpacing: "0.1em" }}
          >
            Εμπιστευτικό &mdash; Παρουσίαση Εταίρων
          </p>
        </div>
      </div>

      {/* Slide number */}
      <div
        className="absolute bottom-0 right-0"
        style={{ paddingBottom: "2.4vh", paddingRight: "5vw" }}
      >
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: "1.3vw", color: "rgba(255,255,255,0.35)" }}>10</span>
      </div>
    </div>
  );
}

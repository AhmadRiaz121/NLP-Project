import { useState, useEffect } from "react";
import { T, API } from "./tokens";
import { Loader } from "./Widgets";

export default function LandingScreen({ onStart }) {
  const [companies, setCompanies] = useState([
    { ticker: "AAPL", name: "Apple Inc." },
    { ticker: "MSFT", name: "Microsoft Corp." },
  ]);
  const [selectedTicker, setSelectedTicker] = useState("AAPL");
  const [events, setEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [error, setError] = useState(null);

  // Fetch events when company changes
  useEffect(() => {
    setLoadingEvents(true);
    setError(null);
    fetch(`${API}/api/events/${selectedTicker}`)
      .then(r => r.json())
      .then(data => {
        const evts = (data.events || []).slice(0, 20); // latest 20
        setEvents(evts);
        if (evts.length > 0) setSelectedEvent(evts[0]);
        else setSelectedEvent(null);
      })
      .catch(e => {
        setError("Backend not reachable. Start the backend server first.");
        setEvents([]);
      })
      .finally(() => setLoadingEvents(false));
  }, [selectedTicker]);

  const company = companies.find(c => c.ticker === selectedTicker) || companies[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, padding: "40px 24px", gap: 36, overflowY: "auto" }}>
      {/* Hero */}
      <div style={{ textAlign: "center" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginBottom: 16 }}>
          <div style={{ width: 5, height: 40, background: T.cyan, borderRadius: 2 }} />
          <span style={{ fontFamily: T.fontMono, fontSize: 32, fontWeight: 700, color: T.white, letterSpacing: "0.06em" }}>EARNINGS<span style={{ color: T.cyan }}>EDGE</span></span>
          <div style={{ width: 5, height: 40, background: T.cyan, borderRadius: 2 }} />
        </div>
        <div style={{ fontFamily: T.fontUI, fontSize: 15, color: T.dimText, maxWidth: 520, lineHeight: 1.6 }}>
          Multimodal earnings call intelligence powered by FinBERT NLP analysis. Real-time audio processing, sentiment detection, hedge analysis, and Signal-to-Noise ratio computation.
        </div>
      </div>

      {/* Company Selector */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%", maxWidth: 640 }}>
        <div style={{ fontFamily: T.fontMono, fontSize: 11, color: T.dimText, letterSpacing: "0.08em" }}>SELECT COMPANY</div>
        <div style={{ display: "flex", gap: 10 }}>
          {companies.map(c => (
            <button key={c.ticker} onClick={() => setSelectedTicker(c.ticker)}
              style={{
                fontFamily: T.fontMono, fontSize: 13, padding: "10px 20px", flex: 1,
                background: selectedTicker === c.ticker ? `${T.cyan}22` : T.panel,
                border: `1.5px solid ${selectedTicker === c.ticker ? T.cyan : T.border}`,
                borderRadius: 8, color: selectedTicker === c.ticker ? T.cyan : T.dimText,
                cursor: "pointer", letterSpacing: "0.04em", transition: "all 0.2s",
              }}>
              <div style={{ fontSize: 16, fontWeight: 700 }}>{c.ticker}</div>
              <div style={{ fontSize: 11, marginTop: 4, color: T.muted }}>{c.name}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Quarter Selector */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%", maxWidth: 640 }}>
        <div style={{ fontFamily: T.fontMono, fontSize: 11, color: T.dimText, letterSpacing: "0.08em" }}>SELECT QUARTER</div>
        {loadingEvents ? <Loader text="Fetching available quarters..." /> : error ? (
          <div style={{ fontFamily: T.fontUI, fontSize: 13, color: T.red, background: `${T.red}12`, border: `1px solid ${T.redDim}`, borderRadius: 8, padding: "14px 18px" }}>{error}</div>
        ) : (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", maxHeight: 180, overflowY: "auto" }}>
            {events.map((ev, i) => {
              const sel = selectedEvent && selectedEvent.year === ev.year && selectedEvent.quarter === ev.quarter;
              return (
                <button key={i} onClick={() => setSelectedEvent(ev)}
                  style={{
                    fontFamily: T.fontMono, fontSize: 12, padding: "6px 14px",
                    background: sel ? `${T.cyan}22` : T.panel,
                    border: `1px solid ${sel ? T.cyan : T.border}`,
                    borderRadius: 5, color: sel ? T.cyan : T.dimText,
                    cursor: "pointer", letterSpacing: "0.04em",
                  }}>
                  Q{ev.quarter} {ev.year}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {selectedEvent && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, width: "100%", maxWidth: 640 }}>
          {/* Real-Time Audio */}
          <button onClick={() => onStart(company, selectedEvent, "realtime")}
            style={{
              padding: "22px 24px", background: `${T.cyan}12`, border: `1.5px solid ${T.cyan}`,
              borderRadius: 10, cursor: "pointer", display: "flex", flexDirection: "column",
              alignItems: "flex-start", gap: 6, transition: "all 0.2s",
            }}
            onMouseEnter={e => { e.currentTarget.style.background = `${T.cyan}1E`; e.currentTarget.style.boxShadow = `0 0 30px ${T.cyan}22`; }}
            onMouseLeave={e => { e.currentTarget.style.background = `${T.cyan}12`; e.currentTarget.style.boxShadow = "none"; }}>
            <div style={{ fontFamily: T.fontMono, fontSize: 15, fontWeight: 700, color: T.cyan, letterSpacing: "0.06em" }}>⬤ REAL-TIME AUDIO</div>
            <div style={{ fontFamily: T.fontUI, fontSize: 12, color: T.dimText, textAlign: "left" }}>Stream audio with live NLP analysis, SNR, and sentiment tracking</div>
          </button>

          {/* Full Transcript */}
          <button onClick={() => onStart(company, selectedEvent, "transcript")}
            style={{
              padding: "22px 24px", background: `${T.gold}0C`, border: `1.5px solid ${T.gold}66`,
              borderRadius: 10, cursor: "pointer", display: "flex", flexDirection: "column",
              alignItems: "flex-start", gap: 6, transition: "all 0.2s",
            }}
            onMouseEnter={e => { e.currentTarget.style.background = `${T.gold}18`; }}
            onMouseLeave={e => { e.currentTarget.style.background = `${T.gold}0C`; }}>
            <div style={{ fontFamily: T.fontMono, fontSize: 15, fontWeight: 700, color: T.gold, letterSpacing: "0.06em" }}>≡ FULL ANALYSIS</div>
            <div style={{ fontFamily: T.fontUI, fontSize: 12, color: T.dimText, textAlign: "left" }}>Complete transcript, remarks vs Q&A, slides, and calendar</div>
          </button>
        </div>
      )}

      {/* Stats Row */}
      <div style={{ display: "flex", gap: 32, marginTop: 8 }}>
        {[["FinBERT", "Sentiment Model"], ["SNR", "Signal Quality"], ["Mistral", "Slide Analysis"], ["WebSocket", "Real-Time Stream"]].map(([v, l]) => (
          <div key={l} style={{ textAlign: "center" }}>
            <div style={{ fontFamily: T.fontMono, fontSize: 18, fontWeight: 700, color: T.cyan }}>{v}</div>
            <div style={{ fontFamily: T.fontUI, fontSize: 11, color: T.muted, marginTop: 2 }}>{l}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

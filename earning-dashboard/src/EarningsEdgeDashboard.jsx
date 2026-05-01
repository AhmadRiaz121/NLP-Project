import { useState, useEffect } from "react";
import { T, scoreToColor, scoreToLabel, snrToColor } from "./tokens";
import LandingScreen from "./LandingScreen";
import AudioTab from "./AudioTab";
import TranscriptTab from "./TranscriptTab";
import RemarksTab from "./RemarksTab";
import SlidesTab from "./SlidesTab";
import CalendarTab from "./CalendarTab";
import InsightsTab from "./InsightsTab";

// ─── TOP BAR ─────────────────────────────────────────────────────────────────
function TopBar({ company, event, activeTab, onTabChange, onReset }) {
  const tabs = [
    { id: "audio", label: "⬤ AUDIO", color: T.cyan },
    { id: "transcript", label: "≡ TRANSCRIPT", color: T.gold },
    { id: "remarks", label: "◈ REMARKS vs Q&A", color: T.purple },
    { id: "slides", label: "▤ SLIDES", color: T.green },
    { id: "insights", label: "⚡ INSIGHTS", color: T.purple },
    { id: "calendar", label: "◉ CALENDAR", color: T.dimText },
  ];

  return (
    <div style={{ display: "flex", alignItems: "center", padding: "0 20px", height: 52, borderBottom: `1px solid ${T.border}`, background: T.surface, gap: 16, flexShrink: 0, position: "relative", zIndex: 10 }}>
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginRight: 4, cursor: "pointer" }} onClick={onReset}>
        <div style={{ width: 5, height: 24, background: T.cyan, borderRadius: 2 }} />
        <span style={{ fontFamily: T.fontMono, fontSize: 13, fontWeight: 600, color: T.white, letterSpacing: "0.08em" }}>
          EARNINGS<span style={{ color: T.cyan }}>EDGE</span>
        </span>
      </div>

      <div style={{ width: 1, height: 28, background: T.border }} />

      {/* Company Info */}
      <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
        <div style={{ fontFamily: T.fontMono, fontSize: 14, fontWeight: 700, color: T.white }}>{company?.ticker}</div>
        <div style={{ fontFamily: T.fontUI, fontSize: 10, color: T.dimText }}>{company?.name} · Q{event?.quarter} {event?.year}</div>
      </div>

      <div style={{ width: 1, height: 28, background: T.border }} />

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4 }}>
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => onTabChange(tab.id)}
            style={{
              fontFamily: T.fontMono, fontSize: 11, padding: "6px 14px",
              background: activeTab === tab.id ? `${tab.color}1A` : "transparent",
              border: `1px solid ${activeTab === tab.id ? tab.color + "55" : "transparent"}`,
              borderRadius: 4, color: activeTab === tab.id ? tab.color : T.muted,
              cursor: "pointer", letterSpacing: "0.04em", transition: "all 0.2s",
            }}>
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1 }} />

      <button onClick={onReset} style={{
        fontFamily: T.fontMono, fontSize: 11, color: T.dimText,
        background: "transparent", border: `1px solid ${T.border}`,
        borderRadius: 4, padding: "5px 14px", cursor: "pointer", letterSpacing: "0.06em",
      }}>
        ← NEW CALL
      </button>
    </div>
  );
}

// ─── MAIN EXPORT ─────────────────────────────────────────────────────────────
export default function EarningsEdge() {
  const [screen, setScreen] = useState("landing");
  const [company, setCompany] = useState(null);
  const [event, setEvent] = useState(null);
  const [mode, setMode] = useState(null);
  const [activeTab, setActiveTab] = useState("audio");

  useEffect(() => {
    const link = document.createElement("link");
    link.href = "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap";
    link.rel = "stylesheet";
    document.head.appendChild(link);
  }, []);

  const handleStart = (co, ev, m) => {
    setCompany(co);
    setEvent(ev);
    setMode(m);
    setActiveTab(m === "realtime" ? "audio" : "transcript");
    setScreen("dashboard");
  };

  const handleReset = () => {
    setScreen("landing");
    setCompany(null);
    setEvent(null);
    setMode(null);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: T.bg, color: T.white, overflow: "hidden" }}>
      {screen === "landing" ? (
        <LandingScreen onStart={handleStart} />
      ) : (
        <>
          <TopBar company={company} event={event} activeTab={activeTab} onTabChange={setActiveTab} onReset={handleReset} />
          <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
            {activeTab === "audio" && <AudioTab ticker={company.ticker} year={event.year} quarter={event.quarter} />}
            {activeTab === "transcript" && <TranscriptTab ticker={company.ticker} year={event.year} quarter={event.quarter} />}
            {activeTab === "remarks" && <RemarksTab ticker={company.ticker} year={event.year} quarter={event.quarter} />}
            {activeTab === "slides" && <SlidesTab ticker={company.ticker} year={event.year} quarter={event.quarter} />}
            {activeTab === "insights" && <InsightsTab ticker={company.ticker} year={event.year} quarter={event.quarter} />}
            {activeTab === "calendar" && <CalendarTab />}
          </div>
        </>
      )}
    </div>
  );
}

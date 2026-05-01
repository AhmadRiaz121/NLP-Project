import { useState, useEffect } from "react";
import { T, API } from "./tokens";
import { Loader, Panel } from "./Widgets";

export default function CalendarTab() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dateStr, setDateStr] = useState("2025-01-10");

  const fetchCalendar = (d) => {
    setLoading(true);
    fetch(`${API}/api/calendar?date=${d}`)
      .then(r => r.json())
      .then(data => setEvents(data.events || []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchCalendar(dateStr); }, []);

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Date Picker */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ fontFamily: T.fontMono, fontSize: 11, color: T.dimText }}>CALENDAR DATE:</span>
        <input type="date" value={dateStr} onChange={e => setDateStr(e.target.value)}
          style={{ fontFamily: T.fontMono, fontSize: 12, padding: "6px 12px", background: T.panel, border: `1px solid ${T.border}`, borderRadius: 6, color: T.white, outline: "none" }} />
        <button onClick={() => fetchCalendar(dateStr)}
          style={{ fontFamily: T.fontMono, fontSize: 11, padding: "6px 16px", background: `${T.cyan}18`, border: `1px solid ${T.cyan}`, borderRadius: 6, color: T.cyan, cursor: "pointer" }}>
          FETCH
        </button>
      </div>

      {loading ? <Loader text="Fetching earnings calendar..." /> : events.length === 0 ? (
        <div style={{ textAlign: "center", padding: 40, fontFamily: T.fontUI, fontSize: 13, color: T.muted }}>No earnings events found for this date.</div>
      ) : (
        <Panel title={`EARNINGS EVENTS — ${dateStr}`}>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {events.map((ev, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 16, padding: "10px 14px", background: T.panel, border: `1px solid ${T.border}`, borderRadius: 6 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: T.fontMono, fontSize: 13, fontWeight: 600, color: T.white }}>{ev.company_name}</div>
                  <div style={{ fontFamily: T.fontMono, fontSize: 11, color: T.dimText }}>Q{ev.quarter} {ev.year}</div>
                </div>
                <div style={{ fontFamily: T.fontUI, fontSize: 11, color: T.muted }}>{ev.conference_date}</div>
                <div style={{
                  fontFamily: T.fontMono, fontSize: 10, padding: "3px 10px",
                  background: ev.transcript_ready ? `${T.green}18` : `${T.gold}18`,
                  border: `1px solid ${ev.transcript_ready ? T.greenDim : T.gold}55`,
                  borderRadius: 20, color: ev.transcript_ready ? T.green : T.gold,
                }}>
                  {ev.transcript_ready ? "TRANSCRIPT READY" : "PENDING"}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import { T, API, scoreToColor } from "./tokens";
import { Loader, Panel, MetricChip } from "./Widgets";

function downloadBlob(filename, content, type = "text/plain") {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function InsightsTab({ ticker, year, quarter }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [watchlist, setWatchlist] = useState("AAPL,MSFT");
  const [watchlistDraft, setWatchlistDraft] = useState("AAPL,MSFT");

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`${API}/api/insights/${ticker}/${year}/${quarter}?watchlist=${encodeURIComponent(watchlist)}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [ticker, year, quarter, watchlist]);

  const markdownExport = useMemo(() => {
    if (!data) return "";
    return [
      `# Advanced Insights — ${ticker} Q${quarter} ${year}`,
      "",
      `## Alpha Signal`,
      `- Score: ${data.alpha_signal?.score ?? 0}`,
      `- Label: ${data.alpha_signal?.label ?? "N/A"}`,
      "",
      "## Top Alerts",
      ...(data.alerts || []).slice(0, 10).map(a => `- ${a.time_label} · ${a.event_type} · ${a.text}`),
      "",
      "## Guidance Diff",
      "- New items:",
      ...((data.guidance_diff?.new_items || []).map(i => `  - ${i}`)),
      "- Removed items:",
      ...((data.guidance_diff?.removed_items || []).map(i => `  - ${i}`)),
    ].join("\n");
  }, [data, ticker, quarter, year]);

  if (loading) return <Loader text="Building advanced insights..." />;
  if (error) return <div style={{ padding: 40, textAlign: "center", color: T.red, fontFamily: T.fontMono }}>{error}</div>;
  if (!data) return null;

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <MetricChip label="ALPHA SIGNAL" value={(data.alpha_signal?.score ?? 0).toFixed(3)} color={scoreToColor(data.alpha_signal?.score || 0)} sub={data.alpha_signal?.label} />
        <MetricChip label="KEY MOMENTS" value={(data.key_moments || []).length} color={T.cyan} />
        <MetricChip label="ALERTS" value={(data.alerts || []).length} color={(data.alerts || []).length > 5 ? T.red : T.green} />
        <MetricChip label="QUESTIONS SCORED" value={(data.question_quality || []).length} color={T.gold} />
        <button onClick={() => downloadBlob(`${ticker}-Q${quarter}-${year}-insights.json`, JSON.stringify(data, null, 2), "application/json")} style={{ fontFamily: T.fontMono, background: `${T.cyan}18`, border: `1px solid ${T.cyan}`, color: T.cyan, borderRadius: 6, padding: "8px 12px", cursor: "pointer" }}>Export JSON</button>
        <button onClick={() => downloadBlob(`${ticker}-Q${quarter}-${year}-insights.md`, markdownExport, "text/markdown")} style={{ fontFamily: T.fontMono, background: `${T.purple}18`, border: `1px solid ${T.purple}`, color: T.purple, borderRadius: 6, padding: "8px 12px", cursor: "pointer" }}>Export Markdown</button>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span style={{ fontFamily: T.fontMono, fontSize: 10, color: T.dimText }}>WATCHLIST TICKERS:</span>
        <input
          value={watchlistDraft}
          onChange={e => setWatchlistDraft(e.target.value)}
          placeholder="AAPL,MSFT"
          style={{ fontFamily: T.fontMono, fontSize: 11, color: T.white, background: T.panel, border: `1px solid ${T.border}`, borderRadius: 6, padding: "6px 8px", minWidth: 180 }}
        />
        <button
          onClick={() => setWatchlist(watchlistDraft)}
          style={{ fontFamily: T.fontMono, fontSize: 11, background: `${T.green}18`, border: `1px solid ${T.green}`, color: T.green, borderRadius: 6, padding: "6px 10px", cursor: "pointer" }}
        >
          Update
        </button>
      </div>

      <Panel title="LIVE KEY MOMENTS TIMELINE">
        <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 280, overflow: "auto" }}>
          {(data.key_moments || []).slice(0, 25).map((m, i) => (
            <div key={i} style={{ border: `1px solid ${T.border}`, background: T.panel, borderRadius: 6, padding: "8px 10px" }}>
              <div style={{ fontFamily: T.fontMono, fontSize: 10, color: T.cyan }}>{m.time_label} · {m.event_type}</div>
              <div style={{ fontFamily: T.fontUI, fontSize: 12, color: T.white }}>{m.text}</div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Q&A VS PREPARED REMARKS">
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <MetricChip label="SENTIMENT SHIFT" value={(data.qa_vs_remarks?.delta?.sentiment_shift ?? 0).toFixed(3)} color={scoreToColor(data.qa_vs_remarks?.delta?.sentiment_shift || 0)} />
          <MetricChip label="SNR SHIFT" value={(data.qa_vs_remarks?.delta?.snr_shift_db ?? 0).toFixed(2)} unit=" dB" color={T.gold} />
          <MetricChip label="HEDGE SHIFT" value={(data.qa_vs_remarks?.delta?.hedge_shift ?? 0).toFixed(3)} color={T.red} />
          <MetricChip label="CONFIDENCE SHIFT" value={(data.qa_vs_remarks?.delta?.confidence_shift ?? 0).toFixed(3)} color={T.green} />
        </div>
      </Panel>

      <Panel title="ANALYST QUESTION QUALITY">
        <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 260, overflowY: "auto" }}>
          {(data.question_quality || []).slice(0, 12).map((q, i) => (
            <div key={i} style={{ border: `1px solid ${T.border}`, borderRadius: 6, padding: "8px 10px", background: T.panel }}>
              <div style={{ fontFamily: T.fontMono, fontSize: 10, color: q.label === "high" ? T.green : q.label === "medium" ? T.gold : T.red }}>{q.label.toUpperCase()} · {q.score}</div>
              <div style={{ fontFamily: T.fontUI, fontSize: 12, color: T.white }}>{q.question}</div>
            </div>
          ))}
        </div>
      </Panel>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Panel title="GUIDANCE DIFF">
          <div style={{ fontFamily: T.fontUI, fontSize: 12, color: T.white }}>
            <div style={{ color: T.green, fontFamily: T.fontMono, marginBottom: 6 }}>New Guidance Items</div>
            {(data.guidance_diff?.new_items || []).slice(0, 6).map((g, i) => <div key={i}>- {g}</div>)}
            <div style={{ color: T.red, fontFamily: T.fontMono, margin: "10px 0 6px 0" }}>Removed Guidance Items</div>
            {(data.guidance_diff?.removed_items || []).slice(0, 6).map((g, i) => <div key={i}>- {g}</div>)}
          </div>
        </Panel>
        <Panel title="CONSISTENCY TRACKER">
          <div style={{ fontFamily: T.fontUI, fontSize: 12, color: T.white, marginBottom: 8 }}>{data.consistency_tracker?.trend_summary}</div>
          {(data.consistency_tracker?.history || []).map((h, i) => (
            <div key={i} style={{ fontFamily: T.fontMono, fontSize: 11, color: T.muted, marginBottom: 4 }}>
              Q{h.quarter} {h.year} · Sentiment {h.sentiment?.toFixed(3)} · Guidance refs {h.guidance_mentions}
            </div>
          ))}
        </Panel>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Panel title="SPEAKER CONFIDENCE HEATMAP">
          {(data.speaker_heatmap || []).map((s, i) => (
            <div key={i} style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr 1fr", gap: 8, padding: "6px 0", borderBottom: `1px dashed ${T.border}` }}>
              <div style={{ fontFamily: T.fontMono, fontSize: 11, color: T.white }}>{s.speaker}</div>
              <div style={{ fontFamily: T.fontMono, fontSize: 11, color: scoreToColor(s.sentiment) }}>Sent {s.sentiment.toFixed(2)}</div>
              <div style={{ fontFamily: T.fontMono, fontSize: 11, color: T.gold }}>SNR {s.snr_db.toFixed(1)}</div>
              <div style={{ fontFamily: T.fontMono, fontSize: 11, color: T.red }}>Hedge {(s.hedge_density * 100).toFixed(1)}%</div>
            </div>
          ))}
        </Panel>
        <Panel title="WATCHLIST SNAPSHOT">
          {(data.watchlist_snapshot || []).map((w, i) => (
            <div key={i} style={{ padding: "8px 10px", border: `1px solid ${T.border}`, borderRadius: 6, background: T.panel, marginBottom: 8 }}>
              <div style={{ fontFamily: T.fontMono, fontSize: 12, color: T.white }}>{w.ticker} · Q{w.quarter} {w.year}</div>
              <div style={{ fontFamily: T.fontMono, fontSize: 11, color: scoreToColor(w.sentiment || 0) }}>
                {w.label} ({(w.sentiment || 0).toFixed(3)})
              </div>
            </div>
          ))}
        </Panel>
      </div>
    </div>
  );
}

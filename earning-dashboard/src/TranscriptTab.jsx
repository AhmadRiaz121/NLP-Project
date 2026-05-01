import { useState, useEffect } from "react";
import { T, API, scoreToColor, snrToColor } from "./tokens";
import { SpeakerBreakdown, SentimentChart, MetricChip, SNRGauge, HedgeGauge, Loader, Panel } from "./Widgets";

export default function TranscriptTab({ ticker, year, quarter }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`${API}/api/analyze/${ticker}/${year}/${quarter}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [ticker, year, quarter]);

  if (loading) return <Loader text="Running FinBERT analysis on full transcript..." />;
  if (error) return <div style={{ padding: 40, textAlign: "center", color: T.red, fontFamily: T.fontMono }}>{error}</div>;
  if (!data) return null;

  const { speakers, overall, sentiment_timeline } = data;
  const overallConfidence = overall.avg_confidence_score ?? ((overall.avg_confidence_density || 0) * 100);
  const chartData = (sentiment_timeline || []).map((s, i) => ({ label: `S${i + 1}`, sentiment: s.sentiment }));

  return (
    <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
      {/* Main Content */}
      <div style={{ flex: 1, overflow: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Overall Metrics */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <MetricChip label="COMPOSITE SENTIMENT" value={overall.composite_sentiment >= 0 ? "+" : ""} unit={overall.composite_sentiment?.toFixed(3)} color={scoreToColor(overall.composite_sentiment || 0)} sub={overall.composite_label} />
          <MetricChip label="WEIGHTED SNR" value={overall.weighted_snr_db?.toFixed(1)} unit=" dB" color={snrToColor(overall.weighted_snr_db || 0)} sub={overall.weighted_snr_db > 8 ? "Strong signal quality" : "Moderate signal"} />
          <MetricChip label="AVG HEDGE" value={Math.round((overall.avg_hedge_density || 0) * 100)} unit="%" color={overall.avg_hedge_density > 0.05 ? T.red : T.green} sub={overall.avg_hedge_density > 0.05 ? "Elevated uncertainty" : "Normal range"} />
          <MetricChip label="CONFIDENCE" value={overallConfidence.toFixed(1)} unit="%" color={overallConfidence >= 55 ? T.green : overallConfidence >= 35 ? T.gold : T.red} sub={overallConfidence >= 55 ? "High conviction language" : overallConfidence >= 35 ? "Moderate conviction" : "Low conviction / cautious"} />
          <MetricChip label="TOTAL WORDS" value={overall.total_words?.toLocaleString()} color={T.cyan} />
          <MetricChip label="SPEAKERS" value={overall.total_speakers} color={T.cyan} />
        </div>

        {/* Sentiment Timeline */}
        <Panel title="SENTIMENT TIMELINE">
          <SentimentChart data={chartData} height={240} />
        </Panel>

        {/* Speaker Breakdown */}
        <Panel title="SPEAKER SENTIMENT & SNR BREAKDOWN">
          <SpeakerBreakdown speakers={speakers} />
        </Panel>

        {/* Speaker Details */}
        {speakers?.map((sp, i) => (
          <Panel key={i} title={`${sp.name || sp.speaker} ${sp.title ? `· ${sp.title}` : ""}`}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginBottom: 12 }}>
              <div style={{ padding: "6px 10px", background: T.panel, borderRadius: 4, border: `1px solid ${T.border}` }}>
                <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>SENTIMENT</div>
                <div style={{ fontFamily: T.fontMono, fontSize: 14, fontWeight: 700, color: scoreToColor(sp.sentiment?.score || 0) }}>{(sp.sentiment?.score || 0).toFixed(3)}</div>
              </div>
              <div style={{ padding: "6px 10px", background: T.panel, borderRadius: 4, border: `1px solid ${T.border}` }}>
                <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>SNR</div>
                <div style={{ fontFamily: T.fontMono, fontSize: 14, fontWeight: 700, color: snrToColor(sp.snr?.snr_db || 0) }}>{(sp.snr?.snr_db || 0).toFixed(1)} dB</div>
              </div>
              <div style={{ padding: "6px 10px", background: T.panel, borderRadius: 4, border: `1px solid ${T.border}` }}>
                <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>HEDGE</div>
                <div style={{ fontFamily: T.fontMono, fontSize: 14, fontWeight: 700, color: (sp.hedging?.hedge_density || 0) > 0.05 ? T.red : T.green }}>{Math.round((sp.hedging?.hedge_density || 0) * 100)}%</div>
              </div>
              <div style={{ padding: "6px 10px", background: T.panel, borderRadius: 4, border: `1px solid ${T.border}` }}>
                <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>HESITATIONS</div>
                <div style={{ fontFamily: T.fontMono, fontSize: 14, fontWeight: 700, color: (sp.hesitations?.hesitation_count || 0) > 3 ? T.red : T.green }}>{sp.hesitations?.hesitation_count || 0}</div>
              </div>
              <div style={{ padding: "6px 10px", background: T.panel, borderRadius: 4, border: `1px solid ${T.border}` }}>
                <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>WORDS</div>
                <div style={{ fontFamily: T.fontMono, fontSize: 14, fontWeight: 700, color: T.white }}>{sp.word_count}</div>
              </div>
            </div>
            {sp.hedging?.hedge_words?.length > 0 && (
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
                <span style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted, alignSelf: "center" }}>HEDGE WORDS:</span>
                {sp.hedging.hedge_words.slice(0, 10).map((w, j) => (
                  <span key={j} style={{ fontFamily: T.fontMono, fontSize: 10, padding: "2px 8px", background: `${T.red}15`, border: `1px solid ${T.redDim}`, borderRadius: 12, color: T.red }}>{w}</span>
                ))}
              </div>
            )}
            <div style={{ fontFamily: T.fontUI, fontSize: 12, color: T.dimText, lineHeight: 1.6, maxHeight: 100, overflow: "auto" }}>{sp.text}</div>
          </Panel>
        ))}
      </div>

      {/* Right Sidebar: SNR Gauges */}
      <div style={{ width: 200, borderLeft: `1px solid ${T.border}`, display: "flex", flexDirection: "column", background: T.surface, flexShrink: 0, padding: "16px 12px", gap: 16, alignItems: "center", overflow: "auto" }}>
        <SNRGauge value={overall.weighted_snr_db || 0} label="WEIGHTED SNR" />
        <div style={{ width: "100%", height: 1, background: T.border }} />
        <HedgeGauge value={overall.avg_hedge_density || 0} />
        <div style={{ width: "100%", height: 1, background: T.border }} />
        <div style={{ fontFamily: T.fontMono, fontSize: 10, color: T.dimText, letterSpacing: "0.08em", textAlign: "center" }}>SNR QUALITY</div>
        <div style={{ fontFamily: T.fontMono, fontSize: 22, fontWeight: 700, color: snrToColor(overall.weighted_snr_db || 0), textAlign: "center" }}>{overall.weighted_snr_db > 8 ? "STRONG" : overall.weighted_snr_db > 2 ? "MODERATE" : "WEAK"}</div>
        <div style={{ fontFamily: T.fontUI, fontSize: 11, color: T.muted, textAlign: "center", lineHeight: 1.5 }}>
          {overall.weighted_snr_db > 8
            ? "High information density. Clear, actionable communication."
            : overall.weighted_snr_db > 2
            ? "Mixed signal clarity. Some hedging present."
            : "Low signal clarity. Significant hedging and uncertainty."}
        </div>
      </div>
    </div>
  );
}

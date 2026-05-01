import { useState, useEffect } from "react";
import { T, API, scoreToColor, snrToColor } from "./tokens";
import { SentimentChart, MetricChip, SNRGauge, Loader, Panel } from "./Widgets";

export default function RemarksTab({ ticker, year, quarter }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/api/remarks/${ticker}/${year}/${quarter}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [ticker, year, quarter]);

  if (loading) return <Loader text="Analyzing Prepared Remarks vs Q&A..." />;
  if (error) return <div style={{ padding: 40, textAlign: "center", color: T.red, fontFamily: T.fontMono }}>{error}</div>;
  if (!data) return null;

  const remarks = data.prepared_remarks;
  const qa = data.qa;
  const ra = remarks?.analysis;
  const qaa = qa?.analysis;

  const remarksChart = (remarks?.timeline || []).map((s, i) => ({ label: `R${i + 1}`, sentiment: s.sentiment }));
  const qaChart = (qa?.timeline || []).map((s, i) => ({ label: `Q${i + 1}`, sentiment: s.sentiment }));
  const remarksConfidence = ra?.confidence?.confidence_score ?? ((ra?.confidence?.confidence_density || 0) * 100);
  const qaConfidence = qaa?.confidence?.confidence_score ?? ((qaa?.confidence?.confidence_density || 0) * 100);

  const ComparisonCard = ({ label, remarksVal, qaVal, unit, colorFn }) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, padding: "12px 16px", background: T.panel, border: `1px solid ${T.border}`, borderRadius: 6, flex: 1, minWidth: 140 }}>
      <div style={{ fontFamily: T.fontMono, fontSize: 10, color: T.dimText, letterSpacing: "0.08em" }}>{label}</div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.cyan }}>REMARKS</div>
          <div style={{ fontFamily: T.fontMono, fontSize: 16, fontWeight: 700, color: colorFn ? colorFn(remarksVal) : T.white }}>{remarksVal}{unit}</div>
        </div>
        <div style={{ width: 1, background: T.border }} />
        <div>
          <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.gold }}>Q&A</div>
          <div style={{ fontFamily: T.fontMono, fontSize: 16, fontWeight: 700, color: colorFn ? colorFn(qaVal) : T.white }}>{qaVal}{unit}</div>
        </div>
      </div>
    </div>
  );

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Comparison Metrics */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <ComparisonCard label="SENTIMENT" remarksVal={(ra?.sentiment?.score || 0).toFixed(3)} qaVal={(qaa?.sentiment?.score || 0).toFixed(3)} unit="" colorFn={v => scoreToColor(parseFloat(v))} />
        <ComparisonCard label="SNR (dB)" remarksVal={(ra?.snr?.snr_db || 0).toFixed(1)} qaVal={(qaa?.snr?.snr_db || 0).toFixed(1)} unit="" colorFn={v => snrToColor(parseFloat(v))} />
        <ComparisonCard label="HEDGE DENSITY" remarksVal={Math.round((ra?.hedging?.hedge_density || 0) * 100)} qaVal={Math.round((qaa?.hedging?.hedge_density || 0) * 100)} unit="%" colorFn={v => parseFloat(v) > 5 ? T.red : T.green} />
        <ComparisonCard label="CONFIDENCE" remarksVal={remarksConfidence.toFixed(1)} qaVal={qaConfidence.toFixed(1)} unit="%" colorFn={v => parseFloat(v) >= 55 ? T.green : parseFloat(v) >= 35 ? T.gold : T.red} />
        <ComparisonCard label="SENTENCES" remarksVal={remarks?.sentence_count || 0} qaVal={qa?.sentence_count || 0} unit="" />
      </div>

      {/* Side by side charts */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Panel title="PREPARED REMARKS — SENTIMENT TIMELINE">
          <SentimentChart data={remarksChart} height={200} />
        </Panel>
        <Panel title="Q&A SESSION — SENTIMENT TIMELINE">
          <SentimentChart data={qaChart} height={200} />
        </Panel>
      </div>

      {/* SNR Comparison Visual */}
      <Panel title="SIGNAL-TO-NOISE RATIO COMPARISON">
        <div style={{ display: "flex", justifyContent: "center", gap: 60, padding: "10px 0" }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontFamily: T.fontMono, fontSize: 11, color: T.cyan, marginBottom: 8 }}>PREPARED REMARKS</div>
            <SNRGauge value={ra?.snr?.snr_db || 0} label="REMARKS SNR" />
          </div>
          <div style={{ width: 1, background: T.border }} />
          <div style={{ textAlign: "center" }}>
            <div style={{ fontFamily: T.fontMono, fontSize: 11, color: T.gold, marginBottom: 8 }}>Q&A SESSION</div>
            <SNRGauge value={qaa?.snr?.snr_db || 0} label="Q&A SNR" />
          </div>
        </div>
        <div style={{ fontFamily: T.fontUI, fontSize: 12, color: T.muted, textAlign: "center", marginTop: 12, lineHeight: 1.6 }}>
          {(ra?.snr?.snr_db || 0) > (qaa?.snr?.snr_db || 0)
            ? "Prepared remarks carry stronger signal than Q&A — executives communicate more clearly in scripted portions."
            : "Q&A session carries stronger signal — executives may be more forthcoming under direct questioning."}
        </div>
      </Panel>

      {/* Text Previews */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Panel title="PREPARED REMARKS PREVIEW">
          <div style={{ fontFamily: T.fontUI, fontSize: 12, color: T.dimText, lineHeight: 1.6, maxHeight: 200, overflow: "auto" }}>{remarks?.text_preview}</div>
        </Panel>
        <Panel title="Q&A SESSION PREVIEW">
          <div style={{ fontFamily: T.fontUI, fontSize: 12, color: T.dimText, lineHeight: 1.6, maxHeight: 200, overflow: "auto" }}>{qa?.text_preview}</div>
        </Panel>
      </div>
    </div>
  );
}

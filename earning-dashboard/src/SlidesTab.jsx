import { useState, useEffect } from "react";
import { T, API } from "./tokens";
import { Loader, Panel } from "./Widgets";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function SlidesTab({ ticker, year, quarter }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/api/slides/${ticker}/${year}/${quarter}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [ticker, year, quarter]);

  if (loading) return <Loader text="Downloading and analyzing slide deck..." />;
  if (error) return (
    <div style={{ padding: 40, textAlign: "center" }}>
      <div style={{ fontFamily: T.fontMono, fontSize: 14, color: T.gold, marginBottom: 8 }}>SLIDE DECK</div>
      <div style={{ fontFamily: T.fontUI, fontSize: 13, color: T.muted }}>Slide deck not available for this quarter. Not all earnings calls include slide presentations.</div>
    </div>
  );

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Status Bar */}
      <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
        <div style={{ padding: "6px 14px", background: data?.status === "success" ? `${T.green}18` : `${T.gold}18`, border: `1px solid ${data?.status === "success" ? T.greenDim : T.gold}55`, borderRadius: 20, fontFamily: T.fontMono, fontSize: 11, color: data?.status === "success" ? T.green : T.gold }}>
          {data?.status === "success" ? "✓ AI ANALYSIS" : data?.status === "fallback" ? "⚠ BASIC ANALYSIS" : "ℹ INFO"}
        </div>
        {data?.model && <span style={{ fontFamily: T.fontMono, fontSize: 11, color: T.dimText }}>Model: {data.model}</span>}
        {data?.slide_count > 0 && <span style={{ fontFamily: T.fontMono, fontSize: 11, color: T.dimText }}>{data.slide_count} slides</span>}
      </div>

      {/* Analysis Content */}
      <Panel title={`SLIDE DECK ANALYSIS — ${ticker} Q${quarter} ${year}`}>
        <div style={{ fontFamily: T.fontUI, fontSize: 13, color: T.white, lineHeight: 1.8, maxHeight: 700, overflow: "auto" }}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => (
                <h1 style={{ fontFamily: T.fontMono, fontSize: 22, margin: "8px 0 14px 0", color: T.cyan }}>{children}</h1>
              ),
              h2: ({ children }) => (
                <h2 style={{ fontFamily: T.fontMono, fontSize: 18, margin: "18px 0 10px 0", color: T.gold }}>{children}</h2>
              ),
              h3: ({ children }) => (
                <h3 style={{ fontFamily: T.fontMono, fontSize: 15, margin: "14px 0 8px 0", color: T.green }}>{children}</h3>
              ),
              p: ({ children }) => (
                <p style={{ margin: "8px 0", color: T.white, lineHeight: 1.75 }}>{children}</p>
              ),
              strong: ({ children }) => (
                <strong style={{ color: T.white, fontWeight: 700 }}>{children}</strong>
              ),
              em: ({ children }) => (
                <em style={{ color: T.muted }}>{children}</em>
              ),
              ul: ({ children }) => (
                <ul style={{ margin: "8px 0 8px 20px", padding: 0 }}>{children}</ul>
              ),
              ol: ({ children }) => (
                <ol style={{ margin: "8px 0 8px 20px", padding: 0 }}>{children}</ol>
              ),
              li: ({ children }) => (
                <li style={{ marginBottom: 6, color: T.white }}>{children}</li>
              ),
              hr: () => (
                <hr style={{ border: 0, borderTop: `1px solid ${T.border}`, margin: "16px 0" }} />
              ),
              code: ({ inline, children }) =>
                inline ? (
                  <code style={{ fontFamily: T.fontMono, fontSize: 12, padding: "2px 6px", background: `${T.cyan}15`, border: `1px solid ${T.cyanDim}`, borderRadius: 4, color: T.cyan }}>
                    {children}
                  </code>
                ) : (
                  <code style={{ display: "block", fontFamily: T.fontMono, fontSize: 12, whiteSpace: "pre-wrap", padding: 10, background: T.panel, border: `1px solid ${T.border}`, borderRadius: 6, color: T.white }}>
                    {children}
                  </code>
                ),
              table: ({ children }) => (
                <div style={{ overflowX: "auto", margin: "10px 0" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, color: T.white }}>
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => (
                <thead style={{ background: `${T.cyan}12` }}>{children}</thead>
              ),
              th: ({ children }) => (
                <th style={{ textAlign: "left", padding: "8px 10px", border: `1px solid ${T.border}`, fontFamily: T.fontMono, fontSize: 11, color: T.cyan }}>
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td style={{ padding: "8px 10px", border: `1px solid ${T.border}`, verticalAlign: "top", color: T.white }}>
                  {children}
                </td>
              ),
              blockquote: ({ children }) => (
                <blockquote style={{ margin: "10px 0", padding: "8px 12px", borderLeft: `3px solid ${T.purple}`, background: `${T.purple}12`, color: T.white }}>
                  {children}
                </blockquote>
              ),
            }}
          >
            {data?.analysis || "No analysis available."}
          </ReactMarkdown>
        </div>
      </Panel>

      {/* Extracted Data */}
      {data?.numbers_found?.length > 0 && (
        <Panel title="FINANCIAL FIGURES DETECTED">
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {data.numbers_found.map((n, i) => (
              <span key={i} style={{ fontFamily: T.fontMono, fontSize: 12, padding: "4px 12px", background: `${T.cyan}15`, border: `1px solid ${T.cyanDim}`, borderRadius: 6, color: T.cyan }}>{n}</span>
            ))}
          </div>
        </Panel>
      )}

      {data?.topics?.length > 0 && (
        <Panel title="KEY TOPICS">
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {data.topics.map((t, i) => (
              <span key={i} style={{ fontFamily: T.fontMono, fontSize: 11, padding: "4px 12px", background: `${T.green}15`, border: `1px solid ${T.greenDim}`, borderRadius: 6, color: T.green }}>{t}</span>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}

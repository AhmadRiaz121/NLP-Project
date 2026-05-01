import { useState, useEffect, useRef } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { T, scoreToColor, snrToColor, snrToLabel } from "./tokens";

// ─── SPEAKER BADGE ───────────────────────────────────────────────────────────
export function SpeakerBadge({ speaker, name, title }) {
  const known = {
    "Operator": T.muted, "spk_0": T.cyan, "spk_1": T.gold, "spk_2": T.red,
    "spk_3": T.purple, "spk_4": T.green, "CEO": T.cyan, "CFO": T.gold,
  };
  const c = known[speaker] || T.cyan;
  const displayName = name || speaker;
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "3px 10px", background: `${c}18`, border: `1px solid ${c}55`, borderRadius: 20, maxWidth: 200 }}>
      <div style={{ width: 6, height: 6, borderRadius: "50%", background: c, flexShrink: 0 }} />
      <span style={{ fontFamily: T.fontMono, fontSize: 10, color: c, letterSpacing: "0.04em", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{displayName}</span>
      {title && <span style={{ fontFamily: T.fontUI, fontSize: 9, color: T.muted, whiteSpace: "nowrap" }}>· {title}</span>}
    </div>
  );
}

// ─── METRIC CHIP ─────────────────────────────────────────────────────────────
export function MetricChip({ label, value, unit = "", color = T.white, sub, icon }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4, padding: "12px 16px", background: T.panel, border: `1px solid ${T.border}`, borderRadius: 6, minWidth: 110, flex: "1 1 110px" }}>
      <div style={{ fontFamily: T.fontMono, fontSize: 10, color: T.dimText, letterSpacing: "0.08em" }}>{icon && `${icon} `}{label}</div>
      <div style={{ fontFamily: T.fontMono, fontSize: 20, fontWeight: 700, color }}>{value}{unit}</div>
      {sub && <div style={{ fontFamily: T.fontUI, fontSize: 11, color: T.muted }}>{sub}</div>}
    </div>
  );
}

// ─── SNR GAUGE (PROMINENT) ───────────────────────────────────────────────────
export function SNRGauge({ value, label = "CONTENT SNR" }) {
  // Map SNR dB (-20 to 30) to 0–1
  const pct = Math.min(1, Math.max(0, (value + 20) / 50));
  const color = snrToColor(value);
  const angle = -135 + pct * 270;
  const r = 48, cx = 65, cy = 65;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const arcPath = (start, end, radius) => {
    const s = { x: cx + radius * Math.cos(toRad(start)), y: cy + radius * Math.sin(toRad(start)) };
    const e = { x: cx + radius * Math.cos(toRad(end)), y: cy + radius * Math.sin(toRad(end)) };
    const large = end - start > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${large} 1 ${e.x} ${e.y}`;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "8px 0" }}>
      <svg width={130} height={90} viewBox="0 0 130 90">
        <path d={arcPath(-135, 135, r)} fill="none" stroke={T.border} strokeWidth={10} strokeLinecap="round" />
        <path d={arcPath(-135, -135 + pct * 270, r)} fill="none" stroke={color} strokeWidth={10} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 6px ${color}88)` }} />
        <line x1={cx} y1={cy} x2={cx + 32 * Math.cos(toRad(angle))} y2={cy + 32 * Math.sin(toRad(angle))} stroke={color} strokeWidth={2.5} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={4} fill={color} />
        <text x={cx} y={cy + 24} textAnchor="middle" fontFamily={T.fontMono} fontSize={16} fontWeight={700} fill={color}>{value.toFixed(1)}</text>
        <text x={cx} y={cy + 36} textAnchor="middle" fontFamily={T.fontMono} fontSize={9} fill={T.dimText}>dB</text>
      </svg>
      <div style={{ fontFamily: T.fontMono, fontSize: 10, color: T.dimText, letterSpacing: "0.08em", marginTop: -4 }}>{label}</div>
      <div style={{ fontFamily: T.fontMono, fontSize: 10, color, marginTop: 2, letterSpacing: "0.06em" }}>{snrToLabel(value)}</div>
    </div>
  );
}

// ─── HEDGE GAUGE ─────────────────────────────────────────────────────────────
export function HedgeGauge({ value }) {
  const pct = Math.min(1, Math.max(0, value));
  const color = pct > 0.6 ? T.red : pct > 0.35 ? T.gold : T.green;
  const angle = -135 + pct * 270;
  const r = 42, cx = 60, cy = 60;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const arcPath = (start, end, radius) => {
    const s = { x: cx + radius * Math.cos(toRad(start)), y: cy + radius * Math.sin(toRad(start)) };
    const e = { x: cx + radius * Math.cos(toRad(end)), y: cy + radius * Math.sin(toRad(end)) };
    const large = end - start > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${large} 1 ${e.x} ${e.y}`;
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <svg width={120} height={80} viewBox="0 0 120 80">
        <path d={arcPath(-135, 135, r)} fill="none" stroke={T.border} strokeWidth={8} strokeLinecap="round" />
        <path d={arcPath(-135, -135 + pct * 270, r)} fill="none" stroke={color} strokeWidth={8} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 4px ${color}88)` }} />
        <line x1={cx} y1={cy} x2={cx + 28 * Math.cos(toRad(angle))} y2={cy + 28 * Math.sin(toRad(angle))} stroke={color} strokeWidth={2.5} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={4} fill={color} />
        <text x={cx} y={cy + 22} textAnchor="middle" fontFamily={T.fontMono} fontSize={14} fontWeight={700} fill={color}>{Math.round(pct * 100)}%</text>
      </svg>
      <div style={{ fontFamily: T.fontMono, fontSize: 10, color: T.dimText, letterSpacing: "0.08em", marginTop: -8 }}>HEDGE DENSITY</div>
    </div>
  );
}

// ─── SENTIMENT CHART ─────────────────────────────────────────────────────────
export function SentimentChart({ data, height = 260 }) {
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const v = payload[0]?.value;
    return (
      <div style={{ background: T.panel, border: `1px solid ${T.borderHi}`, borderRadius: 6, padding: "8px 12px", fontFamily: T.fontMono, fontSize: 11 }}>
        <div style={{ color: T.dimText, marginBottom: 4 }}>{label}</div>
        <div style={{ color: scoreToColor(v), fontSize: 14, fontWeight: 700 }}>{v >= 0 ? "+" : ""}{v?.toFixed(4)}</div>
      </div>
    );
  };
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 4, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="sentGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={T.cyan} stopOpacity={0.15} />
            <stop offset="95%" stopColor={T.cyan} stopOpacity={0.01} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="2 6" stroke={T.border} vertical={false} />
        <XAxis dataKey="label" tick={{ fontFamily: T.fontMono, fontSize: 10, fill: T.muted }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
        <YAxis domain={[-1, 1]} tick={{ fontFamily: T.fontMono, fontSize: 10, fill: T.muted }} axisLine={false} tickLine={false} tickCount={5} />
        <ReferenceLine y={0} stroke={T.border} strokeDasharray="4 4" strokeWidth={1.5} />
        <ReferenceLine y={0.5} stroke={T.greenDim} strokeDasharray="2 6" strokeWidth={1} />
        <ReferenceLine y={-0.5} stroke={T.redDim} strokeDasharray="2 6" strokeWidth={1} />
        <Tooltip content={<CustomTooltip />} />
        <Area type="monotone" dataKey="sentiment" stroke={T.cyan} strokeWidth={2} fill="url(#sentGrad)" dot={false} activeDot={{ r: 4, fill: T.cyan, strokeWidth: 0 }} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ─── AUDIO SNR CHART ─────────────────────────────────────────────────────────
export function AudioSNRChart({ data, height = 260 }) {
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const v = payload[0]?.value;
    return (
      <div style={{ background: T.panel, border: `1px solid ${T.borderHi}`, borderRadius: 6, padding: "8px 12px", fontFamily: T.fontMono, fontSize: 11 }}>
        <div style={{ color: T.dimText, marginBottom: 4 }}>{label}</div>
        <div style={{ color: snrToColor(v), fontSize: 14, fontWeight: 700 }}>{v?.toFixed(1)} dB</div>
      </div>
    );
  };
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 4, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="snrGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={T.green} stopOpacity={0.15} />
            <stop offset="95%" stopColor={T.green} stopOpacity={0.01} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="2 6" stroke={T.border} vertical={false} />
        <XAxis dataKey="label" tick={{ fontFamily: T.fontMono, fontSize: 10, fill: T.muted }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
        <YAxis domain={[-10, 30]} tick={{ fontFamily: T.fontMono, fontSize: 10, fill: T.muted }} axisLine={false} tickLine={false} tickCount={5} />
        <ReferenceLine y={0} stroke={T.border} strokeDasharray="4 4" strokeWidth={1.5} />
        <ReferenceLine y={15} stroke={T.greenDim} strokeDasharray="2 6" strokeWidth={1} />
        <ReferenceLine y={8} stroke={T.goldDim} strokeDasharray="2 6" strokeWidth={1} />
        <Tooltip content={<CustomTooltip />} />
        <Area type="monotone" dataKey="audioSnr" stroke={T.green} strokeWidth={2} fill="url(#snrGrad)" dot={false} activeDot={{ r: 4, fill: T.green, strokeWidth: 0 }} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ─── SPEAKER BREAKDOWN ───────────────────────────────────────────────────────
export function SpeakerBreakdown({ speakers }) {
  if (!speakers || !speakers.length) return null;
  const colors = [T.cyan, T.gold, T.red, T.purple, T.green, T.cyanDim];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {speakers.map((sp, i) => {
        const c = colors[i % colors.length];
        const score = sp.sentiment?.score || 0;
        const barW = Math.max(2, Math.min(100, ((score + 1) / 2) * 100));
        return (
          <div key={i} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <SpeakerBadge speaker={sp.speaker} name={sp.name} title={sp.title} />
              <span style={{ fontFamily: T.fontMono, fontSize: 11, color: scoreToColor(score) }}>
                {score >= 0 ? "+" : ""}{score.toFixed(3)}
              </span>
            </div>
            <div style={{ height: 4, background: T.border, borderRadius: 2, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${barW}%`, background: c, borderRadius: 2, transition: "width 0.4s ease", boxShadow: `0 0 8px ${c}66` }} />
            </div>
            <div style={{ display: "flex", gap: 12, fontFamily: T.fontMono, fontSize: 10, color: T.muted }}>
              <span>{sp.word_count || 0} words</span>
              <span>SNR: {sp.snr?.snr_db?.toFixed(1) || "–"} dB</span>
              <span>Hedge: {((sp.hedging?.hedge_density || 0) * 100).toFixed(1)}%</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── TRANSCRIPT FEED ─────────────────────────────────────────────────────────
export function TranscriptFeed({ lines, follow = true }) {
  const ref = useRef(null);
  useEffect(() => {
    if (follow && ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [lines, follow]);
  return (
    <div ref={ref} style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, padding: "8px 0" }}>
      {lines.map((l, i) => {
        const c = scoreToColor(l.sentiment || 0);
        const isLast = i === lines.length - 1;
        return (
          <div key={i} style={{ padding: "8px 12px", background: isLast ? `${c}0A` : "transparent", borderLeft: `2px solid ${isLast ? c : T.border}`, borderRadius: "0 6px 6px 0", transition: "all 0.3s" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
              <SpeakerBadge speaker={l.speaker} name={l.name} title={l.title} />
              <span style={{ fontFamily: T.fontMono, fontSize: 10, color: T.muted }}>{l.time}</span>
              <span style={{ fontFamily: T.fontMono, fontSize: 10, color: c, marginLeft: "auto" }}>{(l.sentiment || 0) >= 0 ? "+" : ""}{(l.sentiment || 0).toFixed(3)}</span>
            </div>
            <div style={{ fontFamily: T.fontUI, fontSize: 12, color: isLast ? T.white : T.dimText, lineHeight: 1.5 }}>{l.text}</div>
          </div>
        );
      })}
    </div>
  );
}

// ─── LOADING SPINNER ─────────────────────────────────────────────────────────
export function Loader({ text = "Loading..." }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 60, gap: 16 }}>
      <div style={{ width: 32, height: 32, border: `3px solid ${T.border}`, borderTop: `3px solid ${T.cyan}`, borderRadius: "50%", animation: "spin 1s linear infinite" }} />
      <div style={{ fontFamily: T.fontMono, fontSize: 12, color: T.dimText, letterSpacing: "0.06em" }}>{text}</div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ─── PANEL WRAPPER ───────────────────────────────────────────────────────────
export function Panel({ title, children, style = {} }) {
  return (
    <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 8, overflow: "hidden", ...style }}>
      {title && (
        <div style={{ padding: "10px 16px", borderBottom: `1px solid ${T.border}`, fontFamily: T.fontMono, fontSize: 10, color: T.dimText, letterSpacing: "0.08em" }}>{title}</div>
      )}
      <div style={{ padding: "12px 16px" }}>{children}</div>
    </div>
  );
}

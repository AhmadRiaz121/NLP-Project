// ─── DESIGN TOKENS ───────────────────────────────────────────────────────────
export const T = {
  bg:       "#07090D",
  surface:  "#0C1017",
  panel:    "#101520",
  border:   "#1A2333",
  borderHi: "#243044",
  cyan:     "#00C8FF",
  cyanDim:  "#0A8FB3",
  green:    "#00E87A",
  greenDim: "#007A3F",
  red:      "#FF3860",
  redDim:   "#8B1A30",
  gold:     "#FFB547",
  purple:   "#A78BFA",
  white:    "#E8EDF5",
  muted:    "#4A5568",
  dimText:  "#8896A8",
  fontMono: "'IBM Plex Mono', monospace",
  fontUI:   "'IBM Plex Sans', sans-serif",
};

export function scoreToLabel(s) {
  if (s > 0.5) return "STRONGLY BULLISH";
  if (s > 0.2) return "BULLISH";
  if (s > -0.2) return "NEUTRAL";
  if (s > -0.5) return "BEARISH";
  return "STRONGLY BEARISH";
}

export function scoreToColor(s) {
  if (s > 0.2) return T.green;
  if (s > -0.2) return T.gold;
  return T.red;
}

export function snrToColor(db) {
  if (db > 12) return T.green;
  if (db > 5) return T.cyan;
  if (db > 0) return T.gold;
  return T.red;
}

export function snrToLabel(db) {
  if (db > 15) return "EXCELLENT";
  if (db > 8) return "STRONG";
  if (db > 2) return "MODERATE";
  if (db > -5) return "WEAK";
  return "POOR";
}

export const API = ""; // proxy handles it

import { useState, useEffect, useRef } from "react";
import { T, API, scoreToColor, snrToColor } from "./tokens";
import { SpeakerBadge, MetricChip, SNRGauge, HedgeGauge, SentimentChart, AudioSNRChart, TranscriptFeed, Loader } from "./Widgets";

export default function AudioTab({ ticker, year, quarter }) {
  const [status, setStatus] = useState("idle"); // idle | connecting | streaming | complete | error
  const [segments, setSegments] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [transcriptLines, setTranscriptLines] = useState([]);
  const [cumulative, setCumulative] = useState({ composite_score: 0, avg_snr_db: 0, avg_hedge_density: 0, segments_processed: 0 });
  const [totalSegments, setTotalSegments] = useState(0);
  const [totalDuration, setTotalDuration] = useState(0);
  const [audioAvailable, setAudioAvailable] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [engine, setEngine] = useState("");  // <<<< NEW
  const [followAudio, setFollowAudio] = useState(true);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [alerts, setAlerts] = useState([]);
  const wsRef = useRef(null);
  const audioRef = useRef(null);

  const startStream = () => {
    setStatus("connecting");
    setSegments([]);
    setTimeline([]);
    setTranscriptLines([]);
    setErrorMsg("");
    setEngine("");
    setAlerts([]);

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/realtime/${ticker}/${year}/${quarter}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setStatus("streaming");

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "init") {
        setTotalSegments(data.total_segments);
        setTotalDuration(data.total_duration);
        setAudioAvailable(data.audio_available);
        if (data.engine) {
          setEngine(data.engine);   // <<<< NEW
        }
        if (data.audio_available && audioRef.current) {
          audioRef.current.src = `${API}/api/audio/${ticker}/${year}/${quarter}`;
          audioRef.current.onplay = () => {
             if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                 wsRef.current.send("play");
             }
          };
          audioRef.current.play().catch(() => {
             if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                 wsRef.current.send("play");
             }
          });
        } else {
             if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                 wsRef.current.send("play");
             }
        }
      } else if (data.type === "segment") {
        setSegments(prev => [...prev, data]);
        setCumulative(data.cumulative);
        const label = `${Math.floor(data.start_time / 60).toString().padStart(2, "0")}:${Math.floor(data.start_time % 60).toString().padStart(2, "0")}`;
        if (
          (data?.hedging?.hedge_density || 0) > 0.08 ||
          (data?.sentiment?.score || 0) < -0.6 ||
          (data?.hesitations?.hesitation_density || 0) > 0.04
        ) {
          setAlerts(prev => [
            ...prev.slice(-119),
            {
              time: label,
              type: (data?.sentiment?.score || 0) < -0.6 ? "negative-tone" : (data?.hedging?.hedge_density || 0) > 0.08 ? "high-hedge" : "high-hesitation",
              text: data.text?.slice(0, 120) || "(no text)",
            }
          ]);
        }

        // Add to timeline chart
        const audioSnr = data.audio_features?.audio_snr?.audio_snr_db || 0;
        setTimeline(prev => [...prev.slice(-60), { label, audioSnr }]);

        // Add to transcript feed
        if (data.text) {
          setTranscriptLines(prev => [...prev.slice(-30), {
            speaker: data.primary_speaker,
            text: data.text,
            time: label,
            sentiment: data.sentiment.score,
            name: data.primary_speaker,
            title: data.primary_speaker_title,
          }]);
        }
      } else if (data.type === "complete") {
        setStatus("complete");
        setCumulative(prev => ({ ...prev, composite_score: data.final_composite, avg_snr_db: data.final_snr, avg_hedge_density: data.final_hedge }));
      } else if (data.type === "error") {
        setStatus("error");
        setErrorMsg(data.message);
      }
    };

    ws.onerror = () => { setStatus("error"); setErrorMsg("WebSocket connection failed"); };
    ws.onclose = () => { if (status === "streaming") setStatus("complete"); };
  };

  const stopStream = () => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    if (audioRef.current) audioRef.current.pause();
    setStatus("idle");
  };

  useEffect(() => () => { if (wsRef.current) wsRef.current.close(); }, []);
  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = playbackRate;
  }, [playbackRate]);

  const latestSeg = segments[segments.length - 1];
  const progress = totalSegments > 0 ? (cumulative.segments_processed / totalSegments) * 100 : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
      {/* Controls Bar */}
      <div style={{ padding: "12px 20px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 16, background: T.surface }}>
        {status === "idle" || status === "error" ? (
          <button onClick={startStream} style={{ fontFamily: T.fontMono, fontSize: 12, padding: "8px 20px", background: `${T.cyan}18`, border: `1.5px solid ${T.cyan}`, borderRadius: 6, color: T.cyan, cursor: "pointer", letterSpacing: "0.06em" }}>
            ⬤ START REAL-TIME ANALYSIS
          </button>
        ) : status === "streaming" ? (
          <button onClick={stopStream} style={{ fontFamily: T.fontMono, fontSize: 12, padding: "8px 20px", background: `${T.red}18`, border: `1.5px solid ${T.red}`, borderRadius: 6, color: T.red, cursor: "pointer" }}>
            ■ STOP
          </button>
        ) : null}

        {status === "streaming" && (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: T.green, animation: "pulse 1.5s infinite" }} />
            <span style={{ fontFamily: T.fontMono, fontSize: 11, color: T.green }}>PROCESSING</span>
            <span style={{ fontFamily: T.fontMono, fontSize: 11, color: T.dimText }}>{cumulative.segments_processed}/{totalSegments} segments</span>
            {/* WHISPER BADGE */}
            {engine === "whisper" && (
              <span style={{ fontFamily: T.fontMono, fontSize: 10, padding: "2px 8px", background: `${T.purple}15`, border: `1px solid ${T.purple}55`, borderRadius: 4, color: T.purple }}>
                WHISPER
              </span>
            )}
          </div>
        )}
        {status === "complete" && <span style={{ fontFamily: T.fontMono, fontSize: 11, color: T.cyan }}>✓ ANALYSIS COMPLETE</span>}
        {errorMsg && <span style={{ fontFamily: T.fontMono, fontSize: 11, color: T.red }}>{errorMsg}</span>}

        <div style={{ flex: 1 }} />
        {status === "streaming" && (
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: T.fontMono, fontSize: 10, color: T.dimText }}>
            Follow
            <input type="checkbox" checked={followAudio} onChange={e => setFollowAudio(e.target.checked)} />
          </label>
        )}
        <select
          value={playbackRate}
          onChange={e => setPlaybackRate(parseFloat(e.target.value))}
          style={{ fontFamily: T.fontMono, fontSize: 11, background: T.panel, color: T.white, border: `1px solid ${T.border}`, borderRadius: 6, padding: "4px 8px" }}
        >
          <option value={0.75}>0.75x</option>
          <option value={1}>1.0x</option>
          <option value={1.25}>1.25x</option>
          <option value={1.5}>1.5x</option>
        </select>

        {/* Progress Bar */}
        {totalSegments > 0 && (
          <div style={{ width: 120, height: 4, background: T.border, borderRadius: 2, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${progress}%`, background: T.cyan, borderRadius: 2, transition: "width 0.5s ease" }} />
          </div>
        )}
      </div>

      {status === "idle" ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ textAlign: "center", maxWidth: 400 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🎙️</div>
            <div style={{ fontFamily: T.fontMono, fontSize: 14, color: T.dimText, marginBottom: 8 }}>REAL-TIME AUDIO ANALYSIS</div>
            <div style={{ fontFamily: T.fontUI, fontSize: 13, color: T.muted, lineHeight: 1.6 }}>
              Click "Start" to begin streaming the earnings call audio with live FinBERT sentiment analysis, SNR computation, and hedge detection.
            </div>
          </div>
        </div>
      ) : status === "connecting" ? (
        <Loader text="Connecting to analysis stream..." />
      ) : (
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          {/* Left: Live Transcript */}
          <div style={{ width: 300, borderRight: `1px solid ${T.border}`, display: "flex", flexDirection: "column", background: T.surface, flexShrink: 0 }}>
            <div style={{ padding: "10px 14px", borderBottom: `1px solid ${T.border}`, fontFamily: T.fontMono, fontSize: 10, color: T.dimText, letterSpacing: "0.08em" }}>LIVE TRANSCRIPT</div>
            <TranscriptFeed lines={transcriptLines} follow={followAudio} />
          </div>

          {/* Center: Charts */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "auto" }}>
            <div style={{ flex: 1, padding: "16px 20px", minHeight: 250 }}>
              <div style={{ fontFamily: T.fontMono, fontSize: 11, color: T.dimText, letterSpacing: "0.08em", marginBottom: 12 }}>REAL-TIME AUDIO SNR</div>
              <AudioSNRChart data={timeline} height={220} />
            </div>

            {/* Metrics Row */}
            <div style={{ padding: "14px 20px", display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", borderTop: `1px solid ${T.border}` }}>
              <MetricChip label="COMPOSITE" value={cumulative.composite_score >= 0 ? "+" : ""} unit={cumulative.composite_score.toFixed(3)} color={scoreToColor(cumulative.composite_score)} />
              <MetricChip label="AVG SNR" value={cumulative.avg_snr_db.toFixed(1)} unit=" dB" color={snrToColor(cumulative.avg_snr_db)} sub={cumulative.avg_snr_db > 8 ? "Strong signal" : cumulative.avg_snr_db > 2 ? "Moderate" : "Weak signal"} />
              <MetricChip label="HEDGE DENSITY" value={latestSeg ? Math.round(latestSeg.hedging.hedge_density * 100) : 0} unit="%" color={latestSeg && latestSeg.hedging.hedge_density > 0.05 ? T.red : T.green} />
              <MetricChip label="SEGMENTS" value={cumulative.segments_processed} color={T.cyan} sub={`of ${totalSegments}`} />
              <MetricChip label="HESITATIONS" value={latestSeg ? latestSeg.hesitations.hesitation_count : 0} color={latestSeg && latestSeg.hesitations.hesitation_count > 2 ? T.red : T.green} />
              <MetricChip label="AUDIO SNR" value={latestSeg?.audio_features?.audio_snr?.audio_snr_db?.toFixed(1) || 0} unit=" dB" color={latestSeg?.audio_features?.audio_snr?.audio_snr_db > 15 ? T.green : latestSeg?.audio_features?.audio_snr?.audio_snr_db > 8 ? T.gold : T.red} />
            </div>

            {/* Latest Segment Detail */}
            {latestSeg && (
              <div style={{ padding: "14px 20px", borderTop: `1px solid ${T.border}` }}>
                <div style={{ fontFamily: T.fontMono, fontSize: 10, color: T.dimText, marginBottom: 8, letterSpacing: "0.08em" }}>LATEST SEGMENT DETAIL</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10 }}>
                  <div style={{ padding: "8px 12px", background: T.panel, borderRadius: 6, border: `1px solid ${T.border}` }}>
                    <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>SENTIMENT</div>
                    <div style={{ fontFamily: T.fontMono, fontSize: 16, fontWeight: 700, color: scoreToColor(latestSeg.sentiment.score) }}>{latestSeg.sentiment.score >= 0 ? "+" : ""}{latestSeg.sentiment.score.toFixed(3)}</div>
                    <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>{latestSeg.sentiment.label}</div>
                  </div>
                  <div style={{ padding: "8px 12px", background: T.panel, borderRadius: 6, border: `1px solid ${T.border}` }}>
                    <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>SNR</div>
                    <div style={{ fontFamily: T.fontMono, fontSize: 16, fontWeight: 700, color: snrToColor(latestSeg.snr.snr_db) }}>{latestSeg.snr.snr_db.toFixed(1)} dB</div>
                    <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>{latestSeg.snr.quality}</div>
                  </div>
                  <div style={{ padding: "8px 12px", background: T.panel, borderRadius: 6, border: `1px solid ${T.border}` }}>
                    <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>HEDGING</div>
                    <div style={{ fontFamily: T.fontMono, fontSize: 16, fontWeight: 700, color: latestSeg.hedging.hedge_density > 0.05 ? T.red : T.green }}>{Math.round(latestSeg.hedging.hedge_density * 100)}%</div>
                    <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>{latestSeg.hedging.hedge_count} words</div>
                  </div>
                  <div style={{ padding: "8px 12px", background: T.panel, borderRadius: 6, border: `1px solid ${T.border}` }}>
                    <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted }}>SPEAKER</div>
                    <div style={{ fontFamily: T.fontMono, fontSize: 13, fontWeight: 700, color: T.white, marginTop: 2 }}>{latestSeg.primary_speaker}</div>
                    {latestSeg.primary_speaker_title && <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.cyan, marginTop: 2 }}>{latestSeg.primary_speaker_title}</div>}
                    <div style={{ fontFamily: T.fontMono, fontSize: 9, color: T.muted, marginTop: 4 }}>{latestSeg.word_count} words</div>
                  </div>
                </div>
                {latestSeg.hedging.hedge_words?.length > 0 && (
                  <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {latestSeg.hedging.hedge_words.map((w, i) => (
                      <span key={i} style={{ fontFamily: T.fontMono, fontSize: 10, padding: "2px 8px", background: `${T.red}18`, border: `1px solid ${T.redDim}`, borderRadius: 12, color: T.red }}>{w}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right: SNR + Gauges */}
          <div style={{ width: 200, borderLeft: `1px solid ${T.border}`, display: "flex", flexDirection: "column", background: T.surface, flexShrink: 0, padding: "16px 12px", gap: 16, alignItems: "stretch", overflowY: "auto" }}>
            <SNRGauge value={cumulative.avg_snr_db} label="AVG CONTENT SNR" />
            <div style={{ width: "100%", height: 1, background: T.border }} />
            <HedgeGauge value={cumulative.avg_hedge_density} />
            <div style={{ width: "100%", height: 1, background: T.border }} />
            {latestSeg?.audio_features?.audio_snr && (
              <SNRGauge value={latestSeg.audio_features.audio_snr.audio_snr_db || 0} label="AUDIO SNR" />
            )}
            {!!alerts.length && (
              <div style={{ width: "100%", marginTop: 8 }}>
                <div style={{ fontFamily: T.fontMono, fontSize: 10, color: T.red, marginBottom: 6 }}>EVENT ALERTS</div>
                <div style={{ maxHeight: 300, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6, paddingRight: 2 }}>
                  {alerts.map((a, i) => (
                    <div key={i} style={{ padding: "6px 8px", border: `1px solid ${T.redDim}`, background: `${T.red}12`, borderRadius: 6 }}>
                      <div style={{ fontFamily: T.fontMono, fontSize: 10, color: T.red }}>{a.time} · {a.type}</div>
                      <div style={{ fontFamily: T.fontUI, fontSize: 11, color: T.muted }}>{a.text}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      <style>{`@keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:0.3 } }`}</style>
    </div>
  );
}
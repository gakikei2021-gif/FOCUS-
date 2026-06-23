import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

// --- Tone generator using Web Audio API ---
function createAudioEngine() {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const masterGain = ctx.createGain();
  masterGain.gain.value = 0.0;
  masterGain.connect(ctx.destination);

  const nodes = [];

  function ramp(param, target, duration) {
    param.cancelScheduledValues(ctx.currentTime);
    param.setValueAtTime(param.value, ctx.currentTime);
    param.linearRampToValueAtTime(target, ctx.currentTime + duration);
  }

  function addOsc(freq, gainVal, type = "sine") {
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    g.gain.value = gainVal;
    osc.connect(g);
    g.connect(masterGain);
    osc.start();
    nodes.push({ osc, g });
    return { osc, g };
  }

  function addNoise(gainVal) {
    const bufSize = ctx.sampleRate * 2;
    const buf = ctx.createBuffer(1, bufSize, ctx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < bufSize; i++) data[i] = Math.random() * 2 - 1;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    const g = ctx.createGain();
    g.gain.value = gainVal;
    src.connect(filter);
    filter.connect(g);
    g.connect(masterGain);
    src.start();
    nodes.push({ src, g, filter });
    return { src, g, filter };
  }

  const tracks = {
    gamma: () => {
      // Gamma binaural: 40Hz beat via two close tones
      addOsc(200, 0.15, "sine");
      addOsc(240, 0.15, "sine");
      addOsc(400, 0.06, "sine");
    },
    alpha: () => {
      // Alpha binaural: 10Hz beat (relaxed focus)
      addOsc(210, 0.15, "sine");
      addOsc(220, 0.15, "sine");
      addOsc(110, 0.05, "sine");
    },
    brownNoise: () => {
      const { filter, g } = addNoise(0.4);
      filter.frequency.value = 200;
      filter.Q.value = 0.5;
    },
    whiteNoise: () => {
      const { filter, g } = addNoise(0.18);
      filter.type = "highshelf";
      filter.frequency.value = 3000;
      filter.gain.value = -6;
    },
    rain: () => {
      // rain-like: pink-ish noise + gentle rumble
      const { filter: f1 } = addNoise(0.22);
      f1.type = "bandpass";
      f1.frequency.value = 800;
      f1.Q.value = 0.3;
      const { filter: f2 } = addNoise(0.12);
      f2.type = "lowpass";
      f2.frequency.value = 120;
      addOsc(60, 0.04, "sine");
    },
    lofi: () => {
      // Lo-fi: warm bass + soft harmonics
      addOsc(55, 0.12, "sine");
      addOsc(110, 0.06, "sine");
      addOsc(165, 0.03, "triangle");
      addOsc(220, 0.015, "triangle");
      const { filter } = addNoise(0.06);
      filter.type = "lowpass";
      filter.frequency.value = 600;
    },
  };

  return {
    ctx,
    play(trackName, volume = 0.5) {
      // stop existing
      nodes.forEach(({ osc, src }) => {
        try { if (osc) osc.stop(); } catch {}
        try { if (src) src.stop(); } catch {}
      });
      nodes.length = 0;
      masterGain.gain.value = 0;
      if (tracks[trackName]) {
        tracks[trackName]();
        ramp(masterGain.gain, volume, 1.5);
      }
    },
    stop() {
      ramp(masterGain.gain, 0, 1.2);
      setTimeout(() => {
        nodes.forEach(({ osc, src }) => {
          try { if (osc) osc.stop(); } catch {}
          try { if (src) src.stop(); } catch {}
        });
        nodes.length = 0;
      }, 1500);
    },
    setVolume(v) {
      ramp(masterGain.gain, v, 0.3);
    },
  };
}

const SOUND_TRACKS = [
  { id: "gamma", label: "Gamma Waves", desc: "40Hz focus boost", icon: "⚡" },
  { id: "alpha", label: "Alpha Waves", desc: "Calm & alert", icon: "🌊" },
  { id: "brownNoise", label: "Brown Noise", desc: "Deep rumble", icon: "🟫" },
  { id: "whiteNoise", label: "White Noise", desc: "Mask distractions", icon: "🌫️" },
  { id: "rain", label: "Rain", desc: "Gentle rainfall", icon: "🌧️" },
  { id: "lofi", label: "Lo-Fi Tone", desc: "Warm study vibes", icon: "🎵" },
];

const DURATIONS = [25, 45, 60, 90];

export default function DeskGuard() {
  const [screen, setScreen] = useState("setup");
  const [durationMinutes, setDurationMinutes] = useState(45);
  const [password, setPassword] = useState("");
  const [sessionPassword, setSessionPassword] = useState("");
  const [timeLeft, setTimeLeft] = useState(0);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [exitPassword, setExitPassword] = useState("");
  const [shake, setShake] = useState(false);
  const [exitError, setExitError] = useState("");

  // Audio
  const [activeTrack, setActiveTrack] = useState(null);
  const [audioVolume, setAudioVolume] = useState(0.4);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const engineRef = useRef(null);

  // Tasks / Todo
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState("");

  // Breathing exercise
  const [breathMode, setBreathMode] = useState(false);
  const [breathPhase, setBreathPhase] = useState("inhale"); // inhale, hold, exhale
  const [breathCount, setBreathCount] = useState(0);
  const breathTimer = useRef(null);

  // Pomodoro breaks indicator
  const [pomodoroBreaks, setPomodoroBreaks] = useState(0);

  // Affirmation
  const AFFIRMATIONS = [
    "Every minute counts.",
    "Deep work creates real results.",
    "You chose this. Now own it.",
    "Focus is a skill — you're building it now.",
    "The compound effect is real.",
    "Hard things done consistently become easy.",
    "Distractions are temporary. Progress is permanent.",
    "Stay in the room with the problem.",
  ];
  const [affirmIdx, setAffirmIdx] = useState(0);

  useEffect(() => {
    if (screen === "focus") {
      const iv = setInterval(() => {
        setAffirmIdx((i) => (i + 1) % AFFIRMATIONS.length);
      }, 30000);
      return () => clearInterval(iv);
    }
  }, [screen]);

  // Timer
  useEffect(() => {
    let timer;
    if (screen === "focus" && timeLeft > 0) {
      timer = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            setSessionComplete(true);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [screen, timeLeft]);

  const elapsedSeconds = durationMinutes * 60 - timeLeft;
  const canExit = elapsedSeconds >= 300 || sessionComplete;
  const progress = ((durationMinutes * 60 - timeLeft) / (durationMinutes * 60)) * 100;

  const handleStartSession = () => {
    if (password.length < 4) return;
    setSessionPassword(password);
    setTimeLeft(durationMinutes * 60);
    setSessionComplete(false);
    setBreathMode(false);
    setScreen("focus");
  };

  const handleExitAttempt = () => {
    if (!canExit) return;
    if (sessionComplete) { exitFocusMode(); return; }
    setIsPasswordModalOpen(true);
    setExitPassword("");
    setExitError("");
  };

  const verifyExitPassword = () => {
    if (exitPassword === sessionPassword) {
      setIsPasswordModalOpen(false);
      exitFocusMode();
    } else {
      setExitError("Wrong password — stay focused!");
      setShake(true);
      setTimeout(() => setShake(false), 400);
    }
  };

  const exitFocusMode = () => {
    stopAudio();
    setScreen("setup");
    setPassword("");
    setSessionPassword("");
    stopBreathing();
  };

  // Audio controls
  const initEngine = () => {
    if (!engineRef.current) {
      engineRef.current = createAudioEngine();
    }
    if (engineRef.current.ctx.state === "suspended") {
      engineRef.current.ctx.resume();
    }
  };

  const playTrack = (trackId) => {
    initEngine();
    engineRef.current.play(trackId, audioVolume);
    setActiveTrack(trackId);
    setIsAudioPlaying(true);
  };

  const stopAudio = () => {
    if (engineRef.current) engineRef.current.stop();
    setIsAudioPlaying(false);
  };

  const toggleAudio = () => {
    if (isAudioPlaying) {
      stopAudio();
    } else if (activeTrack) {
      playTrack(activeTrack);
    }
  };

  const handleVolumeChange = (e) => {
    const v = parseFloat(e.target.value);
    setAudioVolume(v);
    if (engineRef.current && isAudioPlaying) engineRef.current.setVolume(v);
  };

  // Breathing
  const breathCycles = [
    { phase: "inhale", duration: 4000 },
    { phase: "hold", duration: 4000 },
    { phase: "exhale", duration: 6000 },
  ];
  const breathRef = useRef(0);

  const startBreathing = () => {
    setBreathMode(true);
    setBreathPhase("inhale");
    breathRef.current = 0;
    let idx = 0;
    const step = () => {
      const { phase, duration } = breathCycles[idx % breathCycles.length];
      setBreathPhase(phase);
      if (idx % breathCycles.length === 0 && idx > 0) {
        setBreathCount((c) => c + 1);
      }
      breathTimer.current = setTimeout(step, duration);
      idx++;
    };
    breathTimer.current = setTimeout(step, breathCycles[0].duration);
    setBreathPhase("inhale");
  };

  const stopBreathing = () => {
    clearTimeout(breathTimer.current);
    setBreathMode(false);
  };

  // Tasks
  const addTask = () => {
    if (!newTask.trim()) return;
    setTasks((t) => [...t, { id: Date.now(), text: newTask.trim(), done: false }]);
    setNewTask("");
  };

  const toggleTask = (id) => {
    setTasks((t) => t.map((task) => task.id === id ? { ...task, done: !task.done } : task));
  };

  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  const breathLabel = { inhale: "Breathe In", hold: "Hold", exhale: "Breathe Out" };
  const breathColor = { inhale: "#6ee7b7", hold: "#93c5fd", exhale: "#c4b5fd" };
  const breathScale = { inhale: 1.35, hold: 1.35, exhale: 0.85 };

  return (
    <div style={{ minHeight: "100vh", background: screen === "focus" ? "#050508" : "#0a0a10", display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem", fontFamily: "var(--font-sans, system-ui, sans-serif)", color: "#fff" }}>
      <AnimatePresence mode="wait">
        {screen === "setup" ? (
          <motion.div key="setup" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.4 }}
            style={{ width: "100%", maxWidth: 480, background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.08)", borderRadius: 24, padding: "2rem", boxShadow: "0 32px 80px rgba(0,0,0,0.5)" }}>

            {/* Header */}
            <div style={{ textAlign: "center", marginBottom: "2rem" }}>
              <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 56, height: 56, borderRadius: "50%", background: "rgba(139,92,246,0.15)", marginBottom: 12 }}>
                <span style={{ fontSize: 24 }}>🛡️</span>
              </div>
              <h1 style={{ fontSize: 28, fontWeight: 600, margin: 0, letterSpacing: -0.5 }}>Desk Guard</h1>
              <p style={{ fontSize: 14, color: "rgba(255,255,255,0.4)", margin: "6px 0 0" }}>Set your parameters. Lock in. Do the work.</p>
            </div>

            {/* Duration */}
            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ fontSize: 11, fontWeight: 500, color: "rgba(255,255,255,0.5)", letterSpacing: "0.08em", textTransform: "uppercase", display: "block", marginBottom: 10 }}>⏱ Session Duration</label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 10 }}>
                {DURATIONS.map((m) => (
                  <button key={m} onClick={() => setDurationMinutes(m)}
                    style={{ height: 44, borderRadius: 10, border: durationMinutes === m ? "1.5px solid #8b5cf6" : "0.5px solid rgba(255,255,255,0.1)", background: durationMinutes === m ? "rgba(139,92,246,0.2)" : "rgba(255,255,255,0.04)", color: durationMinutes === m ? "#c4b5fd" : "rgba(255,255,255,0.6)", fontSize: 14, fontWeight: 500, cursor: "pointer", transition: "all 0.15s" }}>
                    {m}m
                  </button>
                ))}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 13, color: "rgba(255,255,255,0.4)", whiteSpace: "nowrap" }}>Custom (mins):</span>
                <input type="number" min={1} value={durationMinutes}
                  onChange={(e) => setDurationMinutes(Math.max(1, parseInt(e.target.value) || 1))}
                  style={{ flex: 1, height: 40, borderRadius: 10, border: "0.5px solid rgba(255,255,255,0.1)", background: "rgba(0,0,0,0.3)", color: "#fff", padding: "0 12px", fontSize: 14, outline: "none" }} />
              </div>
            </div>

            {/* Sound picker */}
            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ fontSize: 11, fontWeight: 500, color: "rgba(255,255,255,0.5)", letterSpacing: "0.08em", textTransform: "uppercase", display: "block", marginBottom: 10 }}>🎧 Focus Sound (optional)</label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
                {SOUND_TRACKS.map((t) => (
                  <button key={t.id} onClick={() => setActiveTrack(activeTrack === t.id ? null : t.id)}
                    style={{ padding: "10px 8px", borderRadius: 10, border: activeTrack === t.id ? "1.5px solid #6ee7b7" : "0.5px solid rgba(255,255,255,0.08)", background: activeTrack === t.id ? "rgba(110,231,183,0.1)" : "rgba(255,255,255,0.03)", color: activeTrack === t.id ? "#6ee7b7" : "rgba(255,255,255,0.55)", cursor: "pointer", textAlign: "left", transition: "all 0.15s" }}>
                    <div style={{ fontSize: 18, marginBottom: 3 }}>{t.icon}</div>
                    <div style={{ fontSize: 12, fontWeight: 500 }}>{t.label}</div>
                    <div style={{ fontSize: 10, opacity: 0.6, marginTop: 2 }}>{t.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Tasks */}
            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ fontSize: 11, fontWeight: 500, color: "rgba(255,255,255,0.5)", letterSpacing: "0.08em", textTransform: "uppercase", display: "block", marginBottom: 10 }}>✅ Session Goals</label>
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <input value={newTask} onChange={(e) => setNewTask(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addTask()}
                  placeholder="What will you accomplish?"
                  style={{ flex: 1, height: 40, borderRadius: 10, border: "0.5px solid rgba(255,255,255,0.1)", background: "rgba(0,0,0,0.3)", color: "#fff", padding: "0 12px", fontSize: 13, outline: "none" }} />
                <button onClick={addTask} style={{ height: 40, padding: "0 14px", borderRadius: 10, background: "rgba(139,92,246,0.2)", border: "1px solid rgba(139,92,246,0.4)", color: "#c4b5fd", cursor: "pointer", fontSize: 20, lineHeight: 1 }}>+</button>
              </div>
              {tasks.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {tasks.map((task) => (
                    <div key={task.id} onClick={() => toggleTask(task.id)}
                      style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.03)", border: "0.5px solid rgba(255,255,255,0.06)", cursor: "pointer" }}>
                      <div style={{ width: 16, height: 16, borderRadius: 4, border: task.done ? "none" : "1.5px solid rgba(255,255,255,0.2)", background: task.done ? "#6ee7b7" : "transparent", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        {task.done && <span style={{ fontSize: 10, color: "#065f46" }}>✓</span>}
                      </div>
                      <span style={{ fontSize: 13, color: task.done ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.75)", textDecoration: task.done ? "line-through" : "none" }}>{task.text}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Password */}
            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{ fontSize: 11, fontWeight: 500, color: "rgba(255,255,255,0.5)", letterSpacing: "0.08em", textTransform: "uppercase", display: "block", marginBottom: 6 }}>🔒 Exit Password</label>
              <p style={{ fontSize: 12, color: "rgba(255,255,255,0.3)", marginBottom: 8 }}>Prevents easy quitting. Minimum 4 characters.</p>
              <input type="password" placeholder="e.g. im-not-quitting" value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ width: "100%", height: 44, borderRadius: 10, border: "0.5px solid rgba(255,255,255,0.1)", background: "rgba(0,0,0,0.3)", color: "#fff", padding: "0 14px", fontSize: 14, outline: "none", boxSizing: "border-box" }} />
            </div>

            <button onClick={handleStartSession} disabled={password.length < 4}
              style={{ width: "100%", height: 52, borderRadius: 14, background: password.length >= 4 ? "#fff" : "rgba(255,255,255,0.1)", color: password.length >= 4 ? "#000" : "rgba(255,255,255,0.3)", fontSize: 16, fontWeight: 600, border: "none", cursor: password.length >= 4 ? "pointer" : "not-allowed", transition: "all 0.2s" }}>
              Start Focus Session →
            </button>
          </motion.div>
        ) : (
          <motion.div key="focus" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.6 }}
            style={{ width: "100%", maxWidth: 560, display: "flex", flexDirection: "column", gap: "1rem" }}>

            {/* Main timer card */}
            <div style={{ background: "rgba(255,255,255,0.03)", border: "0.5px solid rgba(255,255,255,0.07)", borderRadius: 24, padding: "2rem", textAlign: "center", position: "relative", overflow: "hidden" }}>
              {/* Progress arc background */}
              <svg style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", opacity: 0.08, pointerEvents: "none" }} viewBox="0 0 100 100" preserveAspectRatio="none">
                <line x1="0" y1="100" x2="100" y2="100" stroke="#8b5cf6" strokeWidth="0.5" />
                <rect x="0" y="100" width={progress} height="0.5" fill="#8b5cf6" />
              </svg>

              {/* Progress bar */}
              <div style={{ position: "absolute", bottom: 0, left: 0, height: 3, width: `${progress}%`, background: "linear-gradient(90deg, #8b5cf6, #6ee7b7)", borderRadius: "0 2px 0 0", transition: "width 1s linear" }} />

              {sessionComplete ? (
                <div>
                  <div style={{ fontSize: 48, marginBottom: 8 }}>🎉</div>
                  <h2 style={{ fontSize: 22, fontWeight: 600, margin: "0 0 6px", color: "#6ee7b7" }}>Session Complete!</h2>
                  <p style={{ fontSize: 14, color: "rgba(255,255,255,0.4)", margin: 0 }}>Great work. Take a break.</p>
                </div>
              ) : (
                <>
                  <div style={{ fontSize: 13, color: "rgba(255,255,255,0.35)", letterSpacing: "0.1em", marginBottom: 8 }}>FOCUS SESSION</div>
                  <div style={{ fontSize: 72, fontWeight: 700, letterSpacing: -3, lineHeight: 1, marginBottom: 8, fontVariantNumeric: "tabular-nums" }}>
                    {formatTime(timeLeft)}
                  </div>
                  <div style={{ fontSize: 13, color: "rgba(255,255,255,0.3)" }}>
                    {Math.round(progress)}% complete · {formatTime(elapsedSeconds)} elapsed
                  </div>
                  {!canExit && (
                    <div style={{ display: "inline-flex", alignItems: "center", gap: 6, marginTop: 10, padding: "4px 12px", borderRadius: 20, background: "rgba(239,68,68,0.1)", border: "0.5px solid rgba(239,68,68,0.2)", fontSize: 12, color: "#fca5a5" }}>
                      🔒 Locked for {formatTime(300 - elapsedSeconds)} more
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Affirmation */}
            {!sessionComplete && (
              <AnimatePresence mode="wait">
                <motion.div key={affirmIdx} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.5 }}
                  style={{ textAlign: "center", fontSize: 14, color: "rgba(255,255,255,0.25)", fontStyle: "italic", padding: "0 1rem" }}>
                  "{AFFIRMATIONS[affirmIdx]}"
                </motion.div>
              </AnimatePresence>
            )}

            {/* Audio + Breathing row */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              {/* Audio panel */}
              <div style={{ background: "rgba(255,255,255,0.03)", border: "0.5px solid rgba(255,255,255,0.07)", borderRadius: 16, padding: "1rem" }}>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>🎧 Sound</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 10 }}>
                  {SOUND_TRACKS.map((t) => (
                    <button key={t.id}
                      onClick={() => { if (activeTrack === t.id && isAudioPlaying) { stopAudio(); } else { setActiveTrack(t.id); playTrack(t.id); } }}
                      style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 10px", borderRadius: 8, border: (activeTrack === t.id && isAudioPlaying) ? "1px solid #6ee7b7" : "0.5px solid rgba(255,255,255,0.07)", background: (activeTrack === t.id && isAudioPlaying) ? "rgba(110,231,183,0.1)" : "rgba(255,255,255,0.02)", color: (activeTrack === t.id && isAudioPlaying) ? "#6ee7b7" : "rgba(255,255,255,0.5)", cursor: "pointer", textAlign: "left", transition: "all 0.15s", fontSize: 12 }}>
                      <span style={{ fontSize: 14 }}>{t.icon}</span>
                      <span style={{ fontWeight: 500 }}>{t.label}</span>
                      {activeTrack === t.id && isAudioPlaying && <span style={{ marginLeft: "auto", fontSize: 10 }}>▶</span>}
                    </button>
                  ))}
                </div>
                {activeTrack && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>Vol</span>
                    <input type="range" min={0} max={0.9} step={0.05} value={audioVolume} onChange={handleVolumeChange}
                      style={{ flex: 1, accentColor: "#8b5cf6" }} />
                    <button onClick={toggleAudio}
                      style={{ padding: "4px 10px", borderRadius: 8, border: "0.5px solid rgba(255,255,255,0.15)", background: isAudioPlaying ? "rgba(239,68,68,0.15)" : "rgba(110,231,183,0.15)", color: isAudioPlaying ? "#fca5a5" : "#6ee7b7", fontSize: 11, cursor: "pointer" }}>
                      {isAudioPlaying ? "Pause" : "Play"}
                    </button>
                  </div>
                )}
              </div>

              {/* Breathing panel */}
              <div style={{ background: "rgba(255,255,255,0.03)", border: "0.5px solid rgba(255,255,255,0.07)", borderRadius: 16, padding: "1rem", display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 12, alignSelf: "flex-start" }}>🌬️ Breathing</div>
                {!breathMode ? (
                  <>
                    <p style={{ fontSize: 12, color: "rgba(255,255,255,0.3)", textAlign: "center", margin: "0 0 12px", lineHeight: 1.5 }}>4-4-6 box breathing to reset focus</p>
                    <button onClick={startBreathing}
                      style={{ padding: "8px 20px", borderRadius: 10, border: "1px solid rgba(139,92,246,0.4)", background: "rgba(139,92,246,0.1)", color: "#c4b5fd", fontSize: 13, cursor: "pointer" }}>
                      Start
                    </button>
                  </>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
                    <motion.div
                      animate={{ scale: breathScale[breathPhase] }}
                      transition={{ duration: breathPhase === "inhale" ? 4 : breathPhase === "hold" ? 0.1 : 6, ease: breathPhase === "hold" ? "linear" : "easeInOut" }}
                      style={{ width: 64, height: 64, borderRadius: "50%", background: breathColor[breathPhase] + "22", border: `2px solid ${breathColor[breathPhase]}44`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <div style={{ width: 28, height: 28, borderRadius: "50%", background: breathColor[breathPhase] + "66" }} />
                    </motion.div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: breathColor[breathPhase] }}>{breathLabel[breathPhase]}</div>
                    <div style={{ fontSize: 11, color: "rgba(255,255,255,0.3)" }}>{breathCount} cycle{breathCount !== 1 ? "s" : ""}</div>
                    <button onClick={stopBreathing}
                      style={{ padding: "5px 14px", borderRadius: 8, border: "0.5px solid rgba(255,255,255,0.1)", background: "transparent", color: "rgba(255,255,255,0.3)", fontSize: 11, cursor: "pointer" }}>
                      Stop
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Tasks panel */}
            {tasks.length > 0 && (
              <div style={{ background: "rgba(255,255,255,0.03)", border: "0.5px solid rgba(255,255,255,0.07)", borderRadius: 16, padding: "1rem" }}>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>✅ Session Goals — {tasks.filter((t) => t.done).length}/{tasks.length}</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {tasks.map((task) => (
                    <div key={task.id} onClick={() => toggleTask(task.id)}
                      style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.02)", cursor: "pointer" }}>
                      <div style={{ width: 16, height: 16, borderRadius: 4, border: task.done ? "none" : "1.5px solid rgba(255,255,255,0.2)", background: task.done ? "#6ee7b7" : "transparent", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transition: "all 0.2s" }}>
                        {task.done && <span style={{ fontSize: 10, color: "#065f46" }}>✓</span>}
                      </div>
                      <span style={{ fontSize: 13, color: task.done ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.7)", textDecoration: task.done ? "line-through" : "none" }}>{task.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Exit */}
            <div style={{ textAlign: "center" }}>
              <button onClick={handleExitAttempt}
                style={{ padding: "8px 20px", borderRadius: 10, border: "0.5px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.03)", color: canExit ? "rgba(255,255,255,0.5)" : "rgba(255,255,255,0.15)", fontSize: 13, cursor: canExit ? "pointer" : "not-allowed", transition: "all 0.15s" }}>
                {sessionComplete ? "Finish Session" : canExit ? "Exit Session" : "🔒 Locked"}
              </button>
            </div>

            {/* Password modal */}
            <AnimatePresence>
              {isPasswordModalOpen && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50, padding: "1rem" }}>
                  <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: shake ? [1, 1.02, 0.98, 1.02, 1] : 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
                    style={{ width: "100%", maxWidth: 360, background: "#111116", border: "0.5px solid rgba(255,255,255,0.1)", borderRadius: 20, padding: "1.5rem" }}>
                    <h3 style={{ fontSize: 18, fontWeight: 600, margin: "0 0 6px" }}>Exit Focus Mode?</h3>
                    <p style={{ fontSize: 13, color: "rgba(255,255,255,0.4)", margin: "0 0 16px" }}>Enter your exit password to leave early.</p>
                    <input type="password" placeholder="Enter password" value={exitPassword}
                      onChange={(e) => setExitPassword(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && verifyExitPassword()}
                      autoFocus
                      style={{ width: "100%", height: 44, borderRadius: 10, border: exitError ? "1px solid #ef4444" : "0.5px solid rgba(255,255,255,0.1)", background: "rgba(0,0,0,0.4)", color: "#fff", padding: "0 14px", fontSize: 14, outline: "none", boxSizing: "border-box", marginBottom: 8 }} />
                    {exitError && <p style={{ fontSize: 12, color: "#f87171", margin: "0 0 12px" }}>{exitError}</p>}
                    <div style={{ display: "flex", gap: 8 }}>
                      <button onClick={() => setIsPasswordModalOpen(false)}
                        style={{ flex: 1, height: 42, borderRadius: 10, border: "0.5px solid rgba(255,255,255,0.1)", background: "transparent", color: "rgba(255,255,255,0.5)", fontSize: 14, cursor: "pointer" }}>
                        Cancel
                      </button>
                      <button onClick={verifyExitPassword}
                        style={{ flex: 1, height: 42, borderRadius: 10, border: "none", background: "#fff", color: "#000", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
                        Unlock
                      </button>
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

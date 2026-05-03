import { useState, useEffect, useCallback, useRef } from "react";
import "@/App.css";
import { Button } from "./components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { ScrollArea } from "./components/ui/scroll-area";
import { COURSE_CONTENT } from "./data/courseContent";
import {
  Play, Pause, Square, Volume2, Menu, X, CheckCircle2,
  Brain, Server, Container, Activity, HelpCircle, ChevronRight, ChevronLeft,
  Terminal, Shield, Cloud, GitBranch, Database, Layers, BarChart, Globe, Wrench, Volume1, Link,
} from "lucide-react";
import QuizPage from "./components/QuizPage";

const iconMap = {
  Brain, Server, Container, Activity, HelpCircle, Terminal,
  Shield, Cloud, GitBranch, Database, Layers, BarChart, Globe, Wrench, Link,
};

// ─── LocalStorage ─────────────────────────────────────────────────────────────
const STORAGE_KEY = "asd-revision-progress";
const loadProgressFromStorage = () => {
  try { const s = localStorage.getItem(STORAGE_KEY); return s ? JSON.parse(s) : {}; }
  catch { return {}; }
};
const saveProgressToStorage = (progress) => {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(progress)); } catch { /* ignore */ }
};

// ─── Device detection (computed once, stable) ────────────────────────────────
const IS_ANDROID = /Android/i.test(navigator.userAgent);
const IS_MOBILE  = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

// ─── Global cancel token ──────────────────────────────────────────────────────
// Incremented on every new speakText() call so stale onend/onerror callbacks
// from the previous utterance become no-ops.
let gToken = 0;

// ─── Text helpers ─────────────────────────────────────────────────────────────
const MAX_CHUNK = IS_ANDROID ? 130 : 190;

function chunkText(text) {
  if (!text) return [];
  const sentences = text.match(/[^.!?\n]+[.!?\n]+|[^.!?\n]+$/g) || [text];
  const out = [];
  for (const raw of sentences) {
    const s = raw.trim();
    if (!s) continue;
    if (s.length <= MAX_CHUNK) { out.push(s); continue; }
    const parts = s.split(/,\s+/);
    let buf = "";
    for (const p of parts) {
      const c = buf ? buf + ", " + p : p;
      if (c.length > MAX_CHUNK && buf) { out.push(buf.trim()); buf = p; }
      else buf = c;
    }
    if (buf.trim()) {
      if (buf.length > MAX_CHUNK) {
        const words = buf.split(" "); let w = "";
        for (const word of words) {
          const c = w ? w + " " + word : word;
          if (c.length > MAX_CHUNK && w) { out.push(w.trim()); w = word; }
          else w = c;
        }
        if (w.trim()) out.push(w.trim());
      } else { out.push(buf.trim()); }
    }
  }
  return out.filter(Boolean);
}

function transformTextForAudio(text) {
  if (!text) return "";
  let t = text;
  
  // Seulement les transformations essentielles - garder les termes anglais tels quels
  // car les voix modernes (Google, Microsoft) les prononcent correctement en anglais
  const rep = [
    // Extensions de fichiers - prononcer clairement
    [/\.tf\b/g, " point tf"],
    [/\.yml\b/g, " point yml"],
    [/\.yaml\b/g, " point yaml"],
    [/\.py\b/g, " point py"],
    [/\.js\b/g, " point js"],
    [/\.json\b/gi, " point json"],
    [/\.sh\b/g, " point sh"],
    [/\.env\b/g, " point env"],
    [/\.md\b/g, " point md"],
    
    // Slash - garder "slash" pas "barre oblique"
    [/\/32\b/g, " slash 32"],
    [/\/24\b/g, " slash 24"],
    [/\/16\b/g, " slash 16"],
    [/\/0\b/g, " slash 0"],
    [/\//g, " slash "],
    
    // IP addresses - ajouter des pauses
    [/0\.0\.0\.0/g, "0, 0, 0, 0"],
    [/(\d+)\.(\d+)\.(\d+)\.(\d+)/g, "$1, $2, $3, $4"],
    
    // Commandes composées - séparer pour la clarté
    [/\bdocker-compose\b/gi, "docker compose"],
    [/\bfail2ban\b/gi, "fail to ban"],
    
    // Sigles - épeler
    [/\bCI\/CD\b/gi, "CI CD"],
    [/\bSSH\b/g, "S S H"],
    [/\bAPI\b/g, "A P I"],
    [/\bVPC\b/g, "V P C"],
    [/\bEC2\b/g, "E C 2"],
    [/\bS3\b/g, "S 3"],
    [/\bRDS\b/g, "R D S"],
    [/\bIAM\b/g, "I A M"],
    [/\bCPU\b/g, "C P U"],
    [/\bRAM\b/g, "RAM"],
    [/\bDNS\b/g, "D N S"],
    [/\bTLS\b/g, "T L S"],
    [/\bSSL\b/g, "S S L"],
    [/\bHTTPS?\b/g, "H T T P"],
    [/\bYAML\b/gi, "YAML"],
    [/\bJSON\b/gi, "JSON"],
    [/\bHCL\b/g, "H C L"],
    [/\bSLI\b/g, "S L I"],
    [/\bSLO\b/g, "S L O"],
    [/\bSLA\b/g, "S L A"],
    
    // Versions et nombres techniques
    [/\bt2\.micro\b/gi, "t2 micro"],
    [/\bED25519\b/gi, "ED 25519"],
    
    // Nettoyage
    [/\s+/g, " "],
  ];
  
  for (const [p, r] of rep) t = t.replace(p, r);
  return t.trim();
}

function buildUtterance(chunk, voice, rate) {
  const u = new SpeechSynthesisUtterance(chunk);
  u.rate   = rate ?? 0.8;
  u.pitch  = 1.05; // Slightly higher pitch for more natural sound
  u.volume = 1;
  if (voice) { u.voice = voice; u.lang = voice.lang || "fr-FR"; }
  else { u.lang = "fr-FR"; }
  return u;
}

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [course]              = useState(COURSE_CONTENT);
  const [currentSection,  setCurrentSection]  = useState(COURSE_CONTENT[0]);
  const [completedSections, setCompletedSections] = useState(() => {
    const saved = loadProgressFromStorage();
    return new Set(Object.keys(saved).filter(k => saved[k]));
  });
  const [isPlaying,       setIsPlaying]       = useState(false);
  const [currentBlockIndex, setCurrentBlockIndex] = useState(0);
  const [voices,          setVoices]          = useState([]);
  const [selectedVoice,   setSelectedVoice]   = useState(null);
  const [speed,           setSpeed]           = useState(0.8);
  const [sidebarOpen,     setSidebarOpen]     = useState(false);
  const [progress,        setProgress]        = useState(0);
  const [mode,            setMode]            = useState("audio");
  const [ttsMode]         = useState("browser");
  const [edgeVoices,      setEdgeVoices]      = useState([]);
  const [selectedEdgeVoice, setSelectedEdgeVoice] = useState("fr-FR-HenriNeural");
  const [isLoadingAudio,  setIsLoadingAudio]  = useState(false);

  const synthRef          = useRef(window.speechSynthesis);
  const audioRef          = useRef(null); // For Edge TTS audio element
  const continuousRef     = useRef(false);
  const currentIndexRef   = useRef(0);
  const primedRef         = useRef(false); // Android first-play unlock

  // Refs that shadow state so async callbacks always read the latest value
  // without needing to be in the dependency array of useCallback.
  const voiceRef          = useRef(null);
  const speedRef          = useRef(speed);
  const sectionRef        = useRef(currentSection);

  useEffect(() => { voiceRef.current   = selectedVoice;  }, [selectedVoice]);
  useEffect(() => { speedRef.current   = speed;          }, [speed]);
  useEffect(() => { sectionRef.current = currentSection; }, [currentSection]);

  // ── Voice loading - Only best quality voices ────────────────────────────────
  useEffect(() => {
    const synth = synthRef.current;
    const load = () => {
      const all = synth.getVoices();
      if (!all.length) return;
      
      // Filtrer les voix françaises (exclure fr-CA)
      const frVoices = all.filter(v => 
        v.lang?.toLowerCase().startsWith("fr") && 
        !v.lang?.toLowerCase().includes("ca")
      );
      
      if (!frVoices.length) {
        setVoices(all.slice(0, 2));
        setSelectedVoice(all[0]);
        return;
      }
      
      // Trouver la meilleure voix homme et femme
      const findBestVoice = (gender) => {
        const genderKeywords = gender === 'male' 
          ? ['male', 'homme', 'thomas', 'pierre', 'paul', 'henri', 'claude']
          : ['female', 'femme', 'amelie', 'marie', 'denise', 'lea', 'celine'];
        
        // 1. Google (meilleure qualité)
        let voice = frVoices.find(v => 
          v.name.toLowerCase().includes('google') &&
          genderKeywords.some(k => v.name.toLowerCase().includes(k))
        );
        if (voice) return voice;
        
        // 2. Microsoft
        voice = frVoices.find(v => 
          v.name.toLowerCase().includes('microsoft') &&
          genderKeywords.some(k => v.name.toLowerCase().includes(k))
        );
        if (voice) return voice;
        
        // 3. Any with gender keyword
        voice = frVoices.find(v => 
          genderKeywords.some(k => v.name.toLowerCase().includes(k))
        );
        if (voice) return voice;
        
        return null;
      };
      
      const maleVoice = findBestVoice('male');
      const femaleVoice = findBestVoice('female');
      
      // Build final voice list (max 2)
      const finalVoices = [];
      if (maleVoice) finalVoices.push(maleVoice);
      if (femaleVoice && femaleVoice !== maleVoice) finalVoices.push(femaleVoice);
      
      // Fallback if no gender-specific found
      if (finalVoices.length === 0) {
        const google = frVoices.find(v => v.name.toLowerCase().includes('google'));
        const microsoft = frVoices.find(v => v.name.toLowerCase().includes('microsoft'));
        if (google) finalVoices.push(google);
        if (microsoft && microsoft !== google) finalVoices.push(microsoft);
        if (finalVoices.length === 0) finalVoices.push(...frVoices.slice(0, 2));
      }
      
      setVoices(finalVoices);
      
      // Set default: prefer male voice
      setSelectedVoice(prev => {
        if (prev && finalVoices.includes(prev)) return prev;
        return maleVoice || finalVoices[0];
      });
    };
    
    load();
    if (synth.onvoiceschanged !== undefined) synth.onvoiceschanged = load;
    const timers = [100, 300, 700, 1500, 3000].map(ms => setTimeout(load, ms));
    return () => { timers.forEach(clearTimeout); synth.onvoiceschanged = null; };
  }, []);

  // ── Load Edge TTS voices ────────────────────────────────────────────────────
  useEffect(() => {
    const loadEdgeVoices = async () => {
      try {
        const API_BASE = process.env.REACT_APP_BACKEND_URL || "";
        const res = await fetch(`${API_BASE}/api/tts/voices`);
        if (res.ok) {
          const data = await res.json();
          setEdgeVoices(data);
        }
      } catch (e) {
        console.log("Edge voices not available, using defaults");
        setEdgeVoices([
          { name: "fr-FR-DeniseNeural", gender: "Female", locale: "fr-FR" },
          { name: "fr-FR-HenriNeural", gender: "Male", locale: "fr-FR" },
        ]);
      }
    };
    loadEdgeVoices();
  }, []);

  // ── Cleanup on unmount ─────────────────────────────────────────────────────
  useEffect(() => {
    const synth = synthRef.current;
    return () => { try { synth.cancel(); } catch { /* ignore */ } };
  }, []);

  // ── speakText using Browser TTS ──────────────────────────────────────────
  const speakText = useCallback((rawText, onDone) => {
    const synth  = synthRef.current;
    const voice  = voiceRef.current;
    const rate   = speedRef.current;
    const token  = ++gToken;
    const stale  = () => token !== gToken;

    synth.cancel();

    const chunks = chunkText(transformTextForAudio(rawText));
    if (!chunks.length) { onDone?.(); return; }

    const queueAll = () => {
      if (stale()) return;
      chunks.forEach((chunk, idx) => {
        const u      = buildUtterance(chunk, voice, rate);
        const isLast = idx === chunks.length - 1;

        u.onstart = () => { if (!stale()) setIsPlaying(true); };

        u.onend = () => {
          if (stale()) return;
          if (isLast) { setIsPlaying(false); onDone?.(); }
        };

        u.onerror = (e) => {
          if (e?.error === "canceled" || e?.error === "interrupted") return;
          if (stale()) return;
          console.warn("TTS chunk", idx, e?.error);
          if (isLast) { setIsPlaying(false); onDone?.(); }
        };

        try { synth.speak(u); } catch (err) { console.warn("speak() threw:", err); }
      });
    };

    if (IS_ANDROID && !primedRef.current) {
      primedRef.current = true;
      const primer  = buildUtterance(".", voice, 1);
      primer.volume = 0.01;
      const afterPrimer = () => setTimeout(queueAll, 80);
      primer.onend  = afterPrimer;
      primer.onerror = afterPrimer;
      setTimeout(() => { if (!stale()) synth.speak(primer); }, 100);
    } else {
      setTimeout(queueAll, IS_ANDROID ? 110 : 30);
    }
  }, []);

  // ── Block text ─────────────────────────────────────────────────────────────
  const getBlockText = useCallback((block) => {
    // Special handling for tool_card type
    if (block.type === "tool_card") {
      return `Outil : ${block.tool}. ` +
             `Analogie : ${block.analogy}. ` +
             `Ce que ça fait : ${block.description}. ` +
             `Pourquoi c'est utile : ${block.why_useful}. ` +
             `Lien suivant : ${block.link_next}`;
    }
    
    let t = "";
    if (block.title)    t += block.title + ". ";
    if (block.question) t += block.question + " ";
    if (block.answer)   t += "Réponse : " + block.answer;
    else if (block.text) t += block.text;
    return t;
  }, []);

  // ── Section completion ─────────────────────────────────────────────────────
  const markSectionComplete = useCallback(() => {
    const section = sectionRef.current;
    if (!section) return;
    setCompletedSections(prev => {
      const next = new Set([...prev, section.id]);
      const data = {}; next.forEach(id => (data[id] = true));
      saveProgressToStorage(data);
      return next;
    });
  }, []);

  // ── Continuous play ────────────────────────────────────────────────────────
  const playFrom = useCallback((idx) => {
    const section = sectionRef.current;
    if (!section || !continuousRef.current) return;

    if (idx >= section.content.length) {
      continuousRef.current = false;
      setIsPlaying(false);
      markSectionComplete();
      return;
    }

    currentIndexRef.current = idx;
    setCurrentBlockIndex(idx);
    setProgress(((idx + 1) / section.content.length) * 100);

    const text = getBlockText(section.content[idx]);
    if (!text.trim()) { playFrom(idx + 1); return; } // skip empty blocks

    speakText(text, () => {
      if (continuousRef.current) {
        setTimeout(() => playFrom(idx + 1), IS_ANDROID ? 450 : 270);
      }
    });
  }, [getBlockText, speakText, markSectionComplete]);

  // ── Handlers ───────────────────────────────────────────────────────────────
  const handleBlockClick = useCallback((index) => {
    continuousRef.current   = false;
    currentIndexRef.current = index;
    setCurrentBlockIndex(index);
    setProgress(((index + 1) / sectionRef.current.content.length) * 100);
    speakText(getBlockText(sectionRef.current.content[index]), () => {});
  }, [speakText, getBlockText]);

  const togglePlay = useCallback(() => {
    if (isPlaying) {
      synthRef.current.cancel();
      continuousRef.current = false;
      setIsPlaying(false);
    } else {
      continuousRef.current = true;
      playFrom(currentBlockIndex);
    }
  }, [isPlaying, currentBlockIndex, playFrom]);

  const stopPlayback = useCallback(() => {
    synthRef.current.cancel();
    continuousRef.current   = false;
    currentIndexRef.current = 0;
    setIsPlaying(false);
    setCurrentBlockIndex(0);
    setProgress(0);
  }, []);

  const changeSection = useCallback((section) => {
    stopPlayback();
    setCurrentSection(section);
    setCurrentBlockIndex(0);
    currentIndexRef.current = 0;
    setProgress(0);
    setSidebarOpen(false);
  }, [stopPlayback]);

  const navigateSection = useCallback((dir) => {
    const idx = course.findIndex(s => s.id === sectionRef.current?.id);
    const nxt = idx + dir;
    if (nxt >= 0 && nxt < course.length) changeSection(course[nxt]);
  }, [course, changeSection]);

  const changeSpeed = useCallback((val) => {
    const n = parseFloat(val);
    speedRef.current = n;
    setSpeed(n);
    if (isPlaying) stopPlayback();
  }, [isPlaying, stopPlayback]);

  const changeVoice = useCallback((name) => {
    const v = voices.find(v => v.name === name);
    if (!v) return;
    voiceRef.current = v;
    setSelectedVoice(v);
    if (isPlaying) stopPlayback();
  }, [voices, isPlaying, stopPlayback]);

  const getShortVoiceName = (voice) => {
    if (!voice) return "Voix";
    const n = voice.name;
    if (n.includes("Google"))    return n.replace("Google ", "");
    if (n.includes("Microsoft")) return n.split(" ").slice(1, 3).join(" ");
    return n.length > 20 ? n.substring(0, 18) + "…" : n;
  };

  // ── Block renderer ─────────────────────────────────────────────────────────
  const renderBlock = (block, index) => {
    const active  = index === currentBlockIndex && isPlaying;
    const current = index === currentBlockIndex;
    
    // Special rendering for tool_card type
    if (block.type === "tool_card") {
      return (
        <div
          key={index}
          data-testid={`content-block-${index}`}
          className={`tool-card${active ? " speech-highlight" : ""}${current && !isPlaying ? " block-current" : ""}`}
          onClick={() => handleBlockClick(index)}
          title="Cliquez pour écouter"
        >
          <div className="block-play-indicator"><Volume1 size={16} /></div>
          <div className="tool-card-header">
            <span className="tool-emoji">{block.emoji}</span>
            <div className="tool-info">
              <h3 className="tool-name">{block.tool}</h3>
              <p className="tool-analogy">{block.analogy}</p>
            </div>
          </div>
          <div className="tool-card-body">
            <div className="tool-row">
              <span className="tool-label">Ce que ça fait</span>
              <p className="tool-value">{block.description}</p>
            </div>
            <div className="tool-row">
              <span className="tool-label">Pourquoi c'est utile</span>
              <p className="tool-value">{block.why_useful}</p>
            </div>
            <div className="tool-row tool-link">
              <span className="tool-label">Lien suivant</span>
              <p className="tool-value">{block.link_next} <span className="next-arrow">↓ {block.next_tool}</span></p>
            </div>
          </div>
        </div>
      );
    }
    
    return (
      <div
        key={index}
        data-testid={`content-block-${index}`}
        className={`content-block content-${block.type}${active ? " speech-highlight" : ""}${current && !isPlaying ? " block-current" : ""}`}
        onClick={() => handleBlockClick(index)}
        title="Cliquez pour écouter"
      >
        <div className="block-play-indicator"><Volume1 size={16} /></div>
        {block.title    && <h3 className="block-title">{block.title}</h3>}
        {block.question && <p className="qa-question">{block.question}</p>}
        {block.answer   && <p className="qa-answer">{block.answer}</p>}
        {block.text && !block.answer && <p className="block-text">{block.text}</p>}
      </div>
    );
  };

  const sectionIdx       = course.findIndex(s => s.id === currentSection?.id);
  const completionPct    = Math.round((completedSections.size / course.length) * 100);

  // ── JSX ────────────────────────────────────────────────────────────────────
  if (mode === "quiz") {
    return <QuizPage onBack={() => setMode("audio")} />;
  }

  return (
    <div className="app-container" data-testid="app-container">
      <button className="mobile-menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Menu">
        {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`} data-testid="sidebar">
        <div className="sidebar-header">
          <h1 className="font-heading text-xl font-bold">Révision ASD</h1>
          <p className="font-mono text-xs mt-1 uppercase tracking-wider">Titre Pro Juin 2026</p>
          <div className="progress-summary">
            <div className="progress-bar-small">
              <div className="progress-fill-small" style={{ width: `${completionPct}%` }} />
            </div>
            <span className="progress-text">{completionPct}% complété</span>
          </div>
          <button
            onClick={() => { setMode("quiz"); setSidebarOpen(false); }}
            data-testid="open-quiz-btn"
            style={{
              marginTop: "0.85rem",
              width: "100%",
              padding: "0.6rem 0.9rem",
              background: "#ED7D31",
              color: "white",
              border: "none",
              borderRadius: 8,
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.5rem",
              boxShadow: "0 2px 8px rgba(237,125,49,0.35)",
            }}
          >
            📝 Entraînement Dossier Projet : QCM
          </button>
        </div>
        <ScrollArea className="sidebar-nav">
          <nav>
            {course.map((section, idx) => {
              const Icon   = iconMap[section.icon] || Brain;
              const active = currentSection?.id === section.id;
              const done   = completedSections.has(section.id);
              return (
                <div key={section.id}
                  className={`nav-item${active ? " active" : ""}${done ? " completed" : ""}`}
                  onClick={() => changeSection(section)}>
                  <span className="nav-number">{idx + 1}</span>
                  <Icon size={18} />
                  <span className="flex-1 font-body text-sm nav-title">{section.title}</span>
                  {done && <CheckCircle2 size={16} className="text-green-600" />}
                </div>
              );
            })}
          </nav>
        </ScrollArea>
      </aside>

      <main className="main-content" data-testid="main-content">
        <div className="content-area">
          {currentSection && (<>
            <div className="section-header">
              <span className="section-number">Section {sectionIdx + 1} / {course.length}</span>
              <h2 className="section-title">{currentSection.title}</h2>
              <p className="section-hint">
                {IS_MOBILE ? "Appuyez sur un bloc pour l'écouter" : "Cliquez sur un bloc pour l'écouter"}
              </p>
            </div>
            <div data-testid="content-blocks">
              {currentSection.content.map((block, index) => renderBlock(block, index))}
            </div>
            <div className="section-nav">
              <Button variant="outline" onClick={() => navigateSection(-1)}
                disabled={sectionIdx <= 0} className="nav-btn">
                <ChevronLeft size={16} /> Précédent
              </Button>
              <Button variant="outline" onClick={() => navigateSection(1)}
                disabled={sectionIdx >= course.length - 1} className="nav-btn">
                Suivant <ChevronRight size={16} />
              </Button>
            </div>
          </>)}
        </div>
      </main>

      <div className="audio-player" data-testid="audio-player">
        <div className="player-controls">
          <Button size="icon" variant={isPlaying ? "default" : "outline"}
            onClick={togglePlay} className="h-12 w-12 play-btn"
            title={isPlaying ? "Pause" : "Lecture continue"}>
            {isPlaying ? <Pause size={24} /> : <Play size={24} />}
          </Button>
          <Button size="icon" variant="outline" onClick={stopPlayback}
            className="h-10 w-10" title="Stop">
            <Square size={18} />
          </Button>
        </div>

        <div className="player-info">
          <p className="player-title">{currentSection?.title || "Sélectionnez une section"}</p>
          <p className="player-progress">
            Bloc {currentBlockIndex + 1} / {currentSection?.content?.length || 0}
          </p>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>

        <div className="player-settings">
          <div className="setting-group">
            <Volume2 size={16} className="setting-icon" />
            <Select value={selectedVoice?.name || ""} onValueChange={v => setSelectedVoice(voices.find(x => x.name === v))}>
              <SelectTrigger className="voice-select"><SelectValue placeholder="Voix" /></SelectTrigger>
              <SelectContent className="z-[70]">
                {voices.map(v => (
                  <SelectItem key={v.name} value={v.name}>
                    {v.name.toLowerCase().includes('male') || 
                     v.name.toLowerCase().includes('homme') ||
                     v.name.toLowerCase().includes('thomas') ||
                     v.name.toLowerCase().includes('pierre') ||
                     v.name.toLowerCase().includes('henri') ||
                     v.name.toLowerCase().includes('claude')
                      ? "🎙️ Homme" 
                      : "🎙️ Femme"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Select value={speed.toString()} onValueChange={changeSpeed}>
            <SelectTrigger className="speed-select"><SelectValue /></SelectTrigger>
            <SelectContent className="z-[70]">
              {[0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.25, 1.5].map(s =>
                <SelectItem key={s} value={s.toString()}>{s}x</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
}

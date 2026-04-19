import { useState, useEffect, useCallback, useRef } from "react";
import "@/App.css";
import { Button } from "./components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { ScrollArea } from "./components/ui/scroll-area";
import { COURSE_CONTENT } from "./data/courseContent";
import { 
  Play, 
  Pause, 
  Square, 
  Volume2, 
  Menu, 
  X, 
  CheckCircle2,
  Brain,
  Server,
  Container,
  Activity,
  HelpCircle,
  ChevronRight,
  ChevronLeft,
  Terminal,
  Shield,
  Cloud,
  GitBranch,
  Database,
  Layers,
  BarChart,
  Globe,
  Wrench,
  Volume1
} from "lucide-react";

const iconMap = {
  Brain, Server, Container, Activity, HelpCircle, Terminal, 
  Shield, Cloud, GitBranch, Database, Layers, BarChart, Globe, Wrench
};

// LocalStorage helpers
const STORAGE_KEY = "asd-revision-progress";
const loadProgressFromStorage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : {};
  } catch { return {}; }
};
const saveProgressToStorage = (progress) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  } catch { /* ignore */ }
};

function App() {
  const [course] = useState(COURSE_CONTENT);
  const [currentSection, setCurrentSection] = useState(COURSE_CONTENT[0]);
  const [completedSections, setCompletedSections] = useState(() => {
    const saved = loadProgressFromStorage();
    return new Set(Object.keys(saved).filter(k => saved[k]));
  });
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentBlockIndex, setCurrentBlockIndex] = useState(0);
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [speed, setSpeed] = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isMobile, setIsMobile] = useState(false);
  
  const synthRef = useRef(window.speechSynthesis);
  const continuousPlayRef = useRef(false);
  const currentIndexRef = useRef(0);
  const primedRef = useRef(false);
  const isAndroidRef = useRef(/Android/i.test(navigator.userAgent));

  // Detect mobile
  useEffect(() => {
    const checkMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    setIsMobile(checkMobile);
  }, []);

  // Load voices with better mobile support
  useEffect(() => {
    const loadVoices = () => {
      const availableVoices = synthRef.current.getVoices();
      if (availableVoices.length > 0) {
        const frenchVoices = availableVoices.filter(
          v => v.lang && v.lang.toLowerCase().startsWith('fr')
        );
        const voicesToUse = frenchVoices.length > 0 ? frenchVoices : availableVoices;
        setVoices(voicesToUse);
        if (!selectedVoice && voicesToUse.length > 0) {
          const isAndroid = /Android/i.test(navigator.userAgent);
          let chosen = null;
          if (isAndroid) {
            chosen = voicesToUse.find(v => v.localService && v.lang === 'fr-FR')
                 || voicesToUse.find(v => v.localService)
                 || voicesToUse.find(v => v.lang === 'fr-FR')
                 || voicesToUse[0];
          } else {
            chosen = voicesToUse.find(v => v.lang === 'fr-FR') || voicesToUse[0];
          }
          setSelectedVoice(chosen);
        }
      }
    };
    
    loadVoices();
    
    if (synthRef.current.onvoiceschanged !== undefined) {
      synthRef.current.onvoiceschanged = loadVoices;
    }
    
    const timers = [100, 250, 500, 1000, 2000].map(ms => setTimeout(loadVoices, ms));
    return () => timers.forEach(clearTimeout);
  }, [selectedVoice]);

  // Cleanup on unmount
  useEffect(() => {
    const synth = synthRef.current;
    return () => {
      try { synth.cancel(); } catch { /* ignore */ }
    };
  }, []);

  // Transform technical content for audio
  const transformTextForAudio = useCallback((text) => {
    if (!text) return "";
    let t = text;
    const replacements = [
      [/\.tf\b/g, " point TF"], [/\.yml\b/g, " point YAML"], [/\.yaml\b/g, " point YAML"],
      [/\.py\b/g, " point PY"], [/\.js\b/g, " point JS"], [/\.json\b/gi, " point JSON"],
      [/\.sh\b/g, " point SH"], [/\.env\b/g, " point ENV"],
      [/\bdocker-compose\b/gi, "docker compose"], [/\bkubectl\b/gi, "kube control"],
      [/\bsystemctl\b/gi, "system control"], [/\bfail2ban\b/gi, "fail 2 ban"],
      [/\bnginx\b/gi, "engine X"], [/\bterraform\.tfstate\b/gi, "terraform TF state"],
      [/\/32\b/g, " slash 32"], [/\/24\b/g, " slash 24"], [/\/16\b/g, " slash 16"],
      [/0\.0\.0\.0\/0/g, "zéro point zéro point zéro point zéro slash zéro"],
      [/\bCI\/CD\b/gi, "CI CD"], [/\bSLI\b/g, "SLI"], [/\bSLO\b/g, "SLO"], [/\bSLA\b/g, "SLA"],
      [/\bEC2\b/g, "EC2"], [/\bVPC\b/g, "VPC"], [/\bS3\b/g, "S3"], [/\bAWS\b/g, "AWS"],
      [/\bSSH\b/g, "SSH"], [/\bAPI\b/g, "API"], [/\bIP\b/g, "IP"], [/\bCPU\b/g, "CPU"],
      [/\bRAM\b/g, "RAM"], [/\bDNS\b/g, "DNS"], [/\bYAML\b/gi, "YAML"], [/\bJSON\b/gi, "JSON"],
      [/\bt2\.micro\b/g, "T2 micro"], [/\bED25519\b/gi, "ED 25519"],
      [/\s+/g, " "],
    ];
    for (const [p, r] of replacements) t = t.replace(p, r);
    return t.trim();
  }, []);

  const getBlockText = useCallback((block) => {
    let text = "";
    if (block.title) text += block.title + ". ";
    if (block.question) text += block.question + " ";
    if (block.answer) text += "Réponse : " + block.answer;
    else if (block.text) text += block.text;
    return transformTextForAudio(text);
  }, [transformTextForAudio]);

  const markSectionComplete = useCallback(() => {
    if (!currentSection) return;
    const newCompleted = new Set([...completedSections, currentSection.id]);
    setCompletedSections(newCompleted);
    const progressData = {};
    newCompleted.forEach(id => progressData[id] = true);
    saveProgressToStorage(progressData);
  }, [currentSection, completedSections]);

  // Split text into speakable chunks (fixes Chrome Android ~15s cutoff bug)
  const chunkText = useCallback((text, maxLen = 160) => {
    if (!text) return [];
    const sentences = text.match(/[^.!?\n]+[.!?\n]+|[^.!?\n]+$/g) || [text];
    const chunks = [];
    for (const s of sentences) {
      const sentence = s.trim();
      if (!sentence) continue;
      if (sentence.length <= maxLen) {
        chunks.push(sentence);
      } else {
        const parts = sentence.split(/,\s+/);
        let buf = '';
        for (const part of parts) {
          if ((buf + ', ' + part).length > maxLen && buf) {
            chunks.push(buf.trim());
            buf = part;
          } else {
            buf = buf ? buf + ', ' + part : part;
          }
        }
        if (buf.trim()) {
          if (buf.length > maxLen) {
            const words = buf.split(' ');
            let w = '';
            for (const word of words) {
              if ((w + ' ' + word).length > maxLen && w) {
                chunks.push(w.trim());
                w = word;
              } else {
                w = w ? w + ' ' + word : word;
              }
            }
            if (w.trim()) chunks.push(w.trim());
          } else {
            chunks.push(buf.trim());
          }
        }
      }
    }
    return chunks;
  }, []);

  // Core speak function - queues ALL chunks upfront for reliable mobile playback.
  // This avoids the "user gesture lost" issue on Android when chaining via onend.
  const speak = useCallback((text, onEnd) => {
    const synth = synthRef.current;

    if (!text || text.trim() === '') {
      if (onEnd) onEnd();
      return;
    }

    // Prime the engine on first user interaction (required on Android Chrome)
    if (!primedRef.current) {
      try {
        const primer = new SpeechSynthesisUtterance(' ');
        primer.volume = 0;
        primer.rate = 1;
        synth.speak(primer);
      } catch { /* ignore */ }
      primedRef.current = true;
    }

    // Cancel previous speech (kept synchronous — no setTimeout)
    synth.cancel();

    const chunks = chunkText(text, isAndroidRef.current ? 140 : 200);
    if (chunks.length === 0) {
      if (onEnd) onEnd();
      return;
    }

    let finished = 0;
    let firstStartFired = false;

    // Queue all utterances immediately inside the same user gesture.
    // The browser's internal queue will play them sequentially and reliably.
    chunks.forEach((chunk, idx) => {
      const utter = new SpeechSynthesisUtterance(chunk);
      if (selectedVoice) utter.voice = selectedVoice;
      utter.rate = speed;
      utter.lang = (selectedVoice && selectedVoice.lang) || 'fr-FR';
      utter.volume = 1;
      utter.pitch = 1;

      utter.onstart = () => {
        if (!firstStartFired) {
          firstStartFired = true;
          setIsPlaying(true);
        }
      };

      utter.onend = () => {
        finished += 1;
        if (idx === chunks.length - 1) {
          setIsPlaying(false);
          if (onEnd) onEnd();
        }
      };

      utter.onerror = (e) => {
        if (e && (e.error === 'canceled' || e.error === 'interrupted')) {
          return;
        }
        console.warn('Speech error on chunk', idx, ':', e && e.error);
        if (idx === chunks.length - 1 && finished < chunks.length) {
          setIsPlaying(false);
          if (onEnd) onEnd();
        }
      };

      try {
        synth.speak(utter);
      } catch (err) {
        console.warn('speak() threw on chunk', idx, ':', err);
      }
    });
  }, [selectedVoice, speed, chunkText]);

  const handleBlockClick = useCallback((index) => {
    continuousPlayRef.current = false;
    currentIndexRef.current = index;
    setCurrentBlockIndex(index);
    
    const text = getBlockText(currentSection.content[index]);
    setProgress(((index + 1) / currentSection.content.length) * 100);
    
    speak(text, () => {});
  }, [currentSection, getBlockText, speak]);

  const playNextBlock = useCallback(() => {
    if (!continuousPlayRef.current) return;
    
    const nextIndex = currentIndexRef.current + 1;
    
    if (nextIndex >= currentSection.content.length) {
      setIsPlaying(false);
      continuousPlayRef.current = false;
      markSectionComplete();
      return;
    }

    currentIndexRef.current = nextIndex;
    setCurrentBlockIndex(nextIndex);
    
    const text = getBlockText(currentSection.content[nextIndex]);
    setProgress(((nextIndex + 1) / currentSection.content.length) * 100);

    if (!text || text.trim() === '') {
      playNextBlock();
      return;
    }

    speak(text, () => {
      if (continuousPlayRef.current) {
        setTimeout(playNextBlock, 300);
      }
    });
  }, [currentSection, getBlockText, speak, markSectionComplete]);

  const startContinuousPlay = useCallback(() => {
    continuousPlayRef.current = true;
    currentIndexRef.current = currentBlockIndex;
    
    const text = getBlockText(currentSection.content[currentBlockIndex]);
    setProgress(((currentBlockIndex + 1) / currentSection.content.length) * 100);

    speak(text, () => {
      if (continuousPlayRef.current) {
        setTimeout(playNextBlock, 300);
      }
    });
  }, [currentBlockIndex, currentSection, getBlockText, speak, playNextBlock]);

  const togglePlay = useCallback(() => {
    if (isPlaying) {
      synthRef.current.cancel();
      continuousPlayRef.current = false;
      setIsPlaying(false);
    } else {
      startContinuousPlay();
    }
  }, [isPlaying, startContinuousPlay]);

  const stopPlayback = useCallback(() => {
    synthRef.current.cancel();
    continuousPlayRef.current = false;
    setIsPlaying(false);
    setCurrentBlockIndex(0);
    currentIndexRef.current = 0;
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

  const navigateSection = useCallback((direction) => {
    const idx = course.findIndex(s => s.id === currentSection?.id);
    const newIdx = idx + direction;
    if (newIdx >= 0 && newIdx < course.length) {
      changeSection(course[newIdx]);
    }
  }, [course, currentSection, changeSection]);

  const changeSpeed = useCallback((newSpeed) => {
    setSpeed(parseFloat(newSpeed));
    if (isPlaying) {
      stopPlayback();
    }
  }, [isPlaying, stopPlayback]);

  const changeVoice = useCallback((voiceName) => {
    const voice = voices.find(v => v.name === voiceName);
    if (voice) {
      setSelectedVoice(voice);
      if (isPlaying) {
        stopPlayback();
      }
    }
  }, [voices, isPlaying, stopPlayback]);

  const getShortVoiceName = (voice) => {
    if (!voice) return "Voix";
    const name = voice.name;
    if (name.includes("Google")) return name.replace("Google ", "");
    if (name.includes("Microsoft")) return name.split(" ").slice(1, 3).join(" ");
    if (name.length > 20) return name.substring(0, 18) + "...";
    return name;
  };

  const renderBlock = (block, index) => {
    const isActive = index === currentBlockIndex && isPlaying;
    const isCurrent = index === currentBlockIndex;
    const blockClass = `content-block content-${block.type}`;
    
    return (
      <div
        key={index}
        data-testid={`content-block-${index}`}
        className={`${blockClass} ${isActive ? 'speech-highlight' : ''} ${isCurrent && !isPlaying ? 'block-current' : ''}`}
        onClick={() => handleBlockClick(index)}
        title="Cliquez pour écouter"
      >
        <div className="block-play-indicator"><Volume1 size={16} /></div>
        {block.title && <h3 className="block-title">{block.title}</h3>}
        {block.question && <p className="qa-question">{block.question}</p>}
        {block.answer && <p className="qa-answer">{block.answer}</p>}
        {block.text && !block.answer && <p className="block-text">{block.text}</p>}
      </div>
    );
  };

  const currentSectionIndex = course.findIndex(s => s.id === currentSection?.id);
  const completionPercent = Math.round((completedSections.size / course.length) * 100);

  return (
    <div className="app-container" data-testid="app-container">
      <button className="mobile-menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Menu">
        {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`} data-testid="sidebar">
        <div className="sidebar-header">
          <h1 className="font-heading text-xl font-bold">Révision ASD</h1>
          <p className="font-mono text-xs mt-1 uppercase tracking-wider">Titre Pro Juin 2026</p>
          <div className="progress-summary">
            <div className="progress-bar-small">
              <div className="progress-fill-small" style={{ width: `${completionPercent}%` }} />
            </div>
            <span className="progress-text">{completionPercent}% complété</span>
          </div>
        </div>
        
        <ScrollArea className="sidebar-nav">
          <nav>
            {course.map((section, idx) => {
              const Icon = iconMap[section.icon] || Brain;
              const isActive = currentSection?.id === section.id;
              const isCompleted = completedSections.has(section.id);
              return (
                <div
                  key={section.id}
                  className={`nav-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
                  onClick={() => changeSection(section)}
                >
                  <span className="nav-number">{idx + 1}</span>
                  <Icon size={18} />
                  <span className="flex-1 font-body text-sm nav-title">{section.title}</span>
                  {isCompleted && <CheckCircle2 size={16} className="text-green-600" />}
                </div>
              );
            })}
          </nav>
        </ScrollArea>
      </aside>

      <main className="main-content" data-testid="main-content">
        <div className="content-area">
          {currentSection && (
            <>
              <div className="section-header">
                <span className="section-number">Section {currentSectionIndex + 1} / {course.length}</span>
                <h2 className="section-title">{currentSection.title}</h2>
                <p className="section-hint">
                  {isMobile ? "Appuyez sur un bloc pour l'écouter" : "Cliquez sur un bloc pour l'écouter"}
                </p>
              </div>
              
              <div data-testid="content-blocks">
                {currentSection.content.map((block, index) => renderBlock(block, index))}
              </div>
              
              <div className="section-nav">
                <Button variant="outline" onClick={() => navigateSection(-1)} disabled={currentSectionIndex <= 0} className="nav-btn">
                  <ChevronLeft size={16} /> Précédent
                </Button>
                <Button variant="outline" onClick={() => navigateSection(1)} disabled={currentSectionIndex >= course.length - 1} className="nav-btn">
                  Suivant <ChevronRight size={16} />
                </Button>
              </div>
            </>
          )}
        </div>
      </main>

      <div className="audio-player" data-testid="audio-player">
        <div className="player-controls">
          <Button 
            size="icon" 
            variant={isPlaying ? "default" : "outline"} 
            onClick={togglePlay} 
            className="h-12 w-12 play-btn" 
            title={isPlaying ? "Pause" : "Lecture continue"}
          >
            {isPlaying ? <Pause size={24} /> : <Play size={24} />}
          </Button>
          <Button size="icon" variant="outline" onClick={stopPlayback} className="h-10 w-10" title="Stop">
            <Square size={18} />
          </Button>
        </div>

        <div className="player-info">
          <p className="player-title">{currentSection?.title || "Sélectionnez une section"}</p>
          <p className="player-progress">Bloc {currentBlockIndex + 1} / {currentSection?.content?.length || 0}</p>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>

        <div className="player-settings">
          <div className="setting-group">
            <Volume2 size={16} className="setting-icon" />
            <Select value={selectedVoice?.name || ""} onValueChange={changeVoice}>
              <SelectTrigger className="voice-select">
                <SelectValue placeholder="Voix" />
              </SelectTrigger>
              <SelectContent className="z-[70]">
                {voices.length > 0 ? voices.map(v => (
                  <SelectItem key={v.name} value={v.name}>{getShortVoiceName(v)}</SelectItem>
                )) : <SelectItem value="default">Voix système</SelectItem>}
              </SelectContent>
            </Select>
          </div>

          <Select value={speed.toString()} onValueChange={changeSpeed}>
            <SelectTrigger className="speed-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="z-[70]">
              {[0.5, 0.75, 1, 1.25, 1.5, 2].map(s => (
                <SelectItem key={s} value={s.toString()}>{s}x</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
}

export default App;

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
  const [continuousPlay, setContinuousPlay] = useState(true);
  
  const synthRef = useRef(window.speechSynthesis);

  // Load French voices (excluding Canadian French)
  useEffect(() => {
    let retryCount = 0;
    const loadVoices = () => {
      const availableVoices = synthRef.current.getVoices();
      if (availableVoices.length === 0 && retryCount < 10) {
        retryCount++;
        setTimeout(loadVoices, 200);
        return;
      }
      if (availableVoices.length > 0) {
        const frenchVoices = availableVoices.filter(
          v => v.lang.startsWith('fr') && !v.lang.includes('CA')
        );
        const voicesToUse = frenchVoices.length > 0 ? frenchVoices : availableVoices.slice(0, 5);
        setVoices(voicesToUse);
        if (!selectedVoice && voicesToUse.length > 0) {
          const frFR = voicesToUse.find(v => v.lang === 'fr-FR');
          setSelectedVoice(frFR || voicesToUse[0]);
        }
      }
    };
    loadVoices();
    if (synthRef.current.onvoiceschanged !== undefined) {
      synthRef.current.onvoiceschanged = loadVoices;
    }
    setTimeout(loadVoices, 500);
  }, [selectedVoice]);

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

  // Get text for a block
  const getBlockText = useCallback((block) => {
    let text = "";
    if (block.title) text += block.title + ". ";
    if (block.question) text += block.question + " ";
    if (block.answer) text += "Réponse : " + block.answer;
    else if (block.text) text += block.text;
    return transformTextForAudio(text);
  }, [transformTextForAudio]);

  // Speak a single block
  const speakSingleBlock = useCallback((index) => {
    if (!currentSection?.content[index]) return;
    synthRef.current.cancel();
    setCurrentBlockIndex(index);
    const text = getBlockText(currentSection.content[index]);
    if (!text) return;
    
    const utterance = new SpeechSynthesisUtterance(text);
    if (selectedVoice) utterance.voice = selectedVoice;
    utterance.rate = speed;
    utterance.lang = 'fr-FR';
    
    utterance.onstart = () => setIsPlaying(true);
    utterance.onend = () => {
      setIsPlaying(false);
      setProgress(((index + 1) / currentSection.content.length) * 100);
    };
    utterance.onerror = () => setIsPlaying(false);
    
    synthRef.current.speak(utterance);
  }, [currentSection, selectedVoice, speed, getBlockText]);

  // Speak with continuous play
  const speakBlock = useCallback((index) => {
    if (!currentSection?.content[index]) return;
    synthRef.current.cancel();
    const text = getBlockText(currentSection.content[index]);
    
    if (!text && continuousPlay) {
      const next = index + 1;
      if (next < currentSection.content.length) {
        setCurrentBlockIndex(next);
        setTimeout(() => speakBlock(next), 100);
      }
      return;
    }
    
    const utterance = new SpeechSynthesisUtterance(text);
    if (selectedVoice) utterance.voice = selectedVoice;
    utterance.rate = speed;
    utterance.lang = 'fr-FR';
    
    utterance.onend = () => {
      const next = index + 1;
      if (next < currentSection.content.length && continuousPlay) {
        setCurrentBlockIndex(next);
        setTimeout(() => speakBlock(next), 300);
      } else {
        setIsPlaying(false);
        if (next >= currentSection.content.length) markSectionComplete();
      }
    };
    utterance.onerror = () => {
      const next = index + 1;
      if (next < currentSection.content.length && continuousPlay) {
        setCurrentBlockIndex(next);
        setTimeout(() => speakBlock(next), 100);
      } else setIsPlaying(false);
    };
    
    synthRef.current.speak(utterance);
    setProgress(((index + 1) / currentSection.content.length) * 100);
  }, [currentSection, selectedVoice, speed, getBlockText, continuousPlay]);

  // Mark section complete
  const markSectionComplete = () => {
    if (!currentSection) return;
    const newCompleted = new Set([...completedSections, currentSection.id]);
    setCompletedSections(newCompleted);
    const progress = {};
    newCompleted.forEach(id => progress[id] = true);
    saveProgressToStorage(progress);
  };

  const togglePlay = () => {
    if (isPlaying) {
      synthRef.current.cancel();
      setIsPlaying(false);
    } else {
      setContinuousPlay(true);
      speakBlock(currentBlockIndex);
      setIsPlaying(true);
    }
  };

  const stopPlayback = () => {
    synthRef.current.cancel();
    setIsPlaying(false);
    setCurrentBlockIndex(0);
    setProgress(0);
  };

  const handleBlockClick = (index) => {
    setContinuousPlay(false);
    speakSingleBlock(index);
  };

  const changeSection = (section) => {
    stopPlayback();
    setCurrentSection(section);
    setCurrentBlockIndex(0);
    setProgress(0);
    setSidebarOpen(false);
  };

  const navigateSection = (direction) => {
    const idx = course.findIndex(s => s.id === currentSection?.id);
    const newIdx = idx + direction;
    if (newIdx >= 0 && newIdx < course.length) changeSection(course[newIdx]);
  };

  const changeSpeed = (newSpeed) => {
    setSpeed(parseFloat(newSpeed));
    if (isPlaying) stopPlayback();
  };

  const changeVoice = (voiceName) => {
    const voice = voices.find(v => v.name === voiceName);
    if (voice) {
      setSelectedVoice(voice);
      if (isPlaying) stopPlayback();
    }
  };

  const getShortVoiceName = (voice) => {
    if (!voice) return "Voix système";
    const name = voice.name;
    if (name.includes("Google")) return name.replace("Google ", "");
    if (name.includes("Microsoft")) return name.split(" ").slice(1, 3).join(" ");
    return name.split(' ').slice(0, 2).join(' ');
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
                <p className="section-hint">Cliquez sur un bloc pour l'écouter</p>
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
          <Button size="icon" variant={isPlaying ? "default" : "outline"} onClick={togglePlay} className="h-12 w-12 play-btn" title={isPlaying ? "Pause" : "Lecture continue"}>
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

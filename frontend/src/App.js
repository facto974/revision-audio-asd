import { useState, useEffect, useCallback, useRef } from "react";
import "@/App.css";
import axios from "axios";
import { Button } from "./components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { ScrollArea } from "./components/ui/scroll-area";
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

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
const API_BASE = BACKEND_URL.replace(/\/+$/, "");

const iconMap = {
  Brain: Brain,
  Server: Server,
  Container: Container,
  Activity: Activity,
  HelpCircle: HelpCircle,
  Terminal: Terminal,
  Shield: Shield,
  Cloud: Cloud,
  GitBranch: GitBranch,
  Database: Database,
  Layers: Layers,
  BarChart: BarChart,
  Globe: Globe,
  Wrench: Wrench
};

function App() {
  const [course, setCourse] = useState([]);
  const [currentSection, setCurrentSection] = useState(null);
  const [completedSections, setCompletedSections] = useState(new Set());
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentBlockIndex, setCurrentBlockIndex] = useState(0);
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [speed, setSpeed] = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [progress, setProgress] = useState(0);
  const [continuousPlay, setContinuousPlay] = useState(true);
  
  const utteranceRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);

  // Fetch course data
  useEffect(() => {
    const fetchCourse = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/course`);
        setCourse(response.data);
        if (response.data.length > 0) {
          setCurrentSection(response.data[0]);
        }
      } catch (e) {
        console.error("Error fetching course:", e);
      }
    };
    fetchCourse();
  }, []);

  // Load French voices (excluding Canadian French)
  useEffect(() => {
    let retryCount = 0;
    const maxRetries = 10;
    
    const loadVoices = () => {
      const availableVoices = synthRef.current.getVoices();
      
      if (availableVoices.length === 0 && retryCount < maxRetries) {
        retryCount++;
        setTimeout(loadVoices, 200);
        return;
      }
      
      if (availableVoices.length > 0) {
        // Filter French voices but exclude Canadian French (fr-CA)
        const frenchVoices = availableVoices.filter(
          voice => voice.lang.startsWith('fr') && !voice.lang.includes('CA')
        );
        
        const voicesToUse = frenchVoices.length > 0 ? frenchVoices : availableVoices.slice(0, 5);
        setVoices(voicesToUse);
        
        if (!selectedVoice && voicesToUse.length > 0) {
          // Prefer fr-FR voice if available
          const frFRVoice = voicesToUse.find(v => v.lang === 'fr-FR');
          setSelectedVoice(frFRVoice || voicesToUse[0]);
        }
      }
    };

    loadVoices();
    
    if (synthRef.current.onvoiceschanged !== undefined) {
      synthRef.current.onvoiceschanged = loadVoices;
    }
    
    const timeoutId = setTimeout(loadVoices, 500);
    return () => clearTimeout(timeoutId);
  }, [selectedVoice]);

  // Load progress from backend
  useEffect(() => {
    const loadProgress = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/progress`);
        const completed = new Set(
          response.data
            .filter(p => p.completed)
            .map(p => p.section_id)
        );
        setCompletedSections(completed);
      } catch (e) {
        console.error("Error loading progress:", e);
      }
    };
    loadProgress();
  }, []);

  // Transform technical content for better audio reading
  const transformTextForAudio = useCallback((text) => {
    if (!text) return "";
    
    let audioText = text;
    
    // Replace common technical patterns for better pronunciation
    const replacements = [
      // File extensions
      [/\.tf\b/g, " point TF"],
      [/\.yml\b/g, " point YAML"],
      [/\.yaml\b/g, " point YAML"],
      [/\.py\b/g, " point PY"],
      [/\.js\b/g, " point JS"],
      [/\.json\b/g, " point JSON"],
      [/\.sh\b/g, " point SH"],
      [/\.env\b/g, " point ENV"],
      [/\.j2\b/g, " point J2"],
      [/\.md\b/g, " point MD"],
      [/\.ini\b/g, " point INI"],
      
      // Common commands - pronounce naturally
      [/\bssh-keygen\b/gi, "SSH keygen"],
      [/\bssh-copy-id\b/gi, "SSH copy ID"],
      [/\bdocker-compose\b/gi, "docker compose"],
      [/\bkubectl\b/gi, "kube control"],
      [/\bsystemctl\b/gi, "system control"],
      [/\bansible-playbook\b/gi, "ansible playbook"],
      [/\bufw\b/gi, "UFW"],
      [/\bsshd_config\b/gi, "SSH D config"],
      [/\bfail2ban\b/gi, "fail 2 ban"],
      [/\bnginx\b/gi, "engine X"],
      [/\bterraform\.tfstate\b/gi, "terraform TF state"],
      [/\btfstate\b/gi, "TF state"],
      [/\bpytest\b/gi, "py test"],
      [/\bstreamlit\b/gi, "streamlit"],
      
      // Network notations
      [/\/32\b/g, " slash 32"],
      [/\/24\b/g, " slash 24"],
      [/\/16\b/g, " slash 16"],
      [/0\.0\.0\.0\/0/g, "0.0.0.0 slash 0"],
      [/\bCIDR\b/gi, "CIDR"],
      
      // Ports
      [/port\s*(\d+)/gi, "port $1"],
      [/:(\d{4,5})\b/g, " port $1"],
      
      // Common abbreviations
      [/\bCI\/CD\b/gi, "CI CD"],
      [/\bIaC\b/g, "Infrastructure as Code"],
      [/\bSLI\b/g, "SLI"],
      [/\bSLO\b/g, "SLO"],
      [/\bSLA\b/g, "SLA"],
      [/\bEC2\b/g, "EC2"],
      [/\bVPC\b/g, "VPC"],
      [/\bS3\b/g, "S3"],
      [/\bAWS\b/g, "AWS"],
      [/\bHTTPS?\b/g, "HTTP"],
      [/\bSSH\b/g, "SSH"],
      [/\bAPI\b/g, "API"],
      [/\bURL\b/g, "URL"],
      [/\bIP\b/g, "IP"],
      [/\bOS\b/g, "OS"],
      [/\bRAM\b/g, "RAM"],
      [/\bCPU\b/g, "CPU"],
      [/\bDNS\b/g, "DNS"],
      [/\bTCP\b/g, "TCP"],
      [/\bUDP\b/g, "UDP"],
      [/\bYAML\b/gi, "YAML"],
      [/\bHCL\b/g, "HCL"],
      [/\bJSON\b/gi, "JSON"],
      
      // Docker/K8s terms
      [/\bt2\.micro\b/g, "T2 micro"],
      [/\bED25519\b/gi, "ED 25519"],
      [/\b-slim\b/g, " slim"],
      [/\b--check\b/g, " check"],
      [/\b-m\b/g, " moins M"],
      [/\b-d\b/g, " moins D"],
      [/\b-f\b/g, " moins F"],
      [/\b-p\b/g, " moins P"],
      [/\b-r\b/g, " moins R"],
      [/\b-y\b/g, " moins Y"],
      [/\b-i\b/g, " moins I"],
      [/\b-it\b/g, " moins IT"],
      
      // Symbols in context
      [/=>/g, " implique "],
      [/<-/g, " reçoit "],
      [/->/g, " vers "],
      [/\|\|/g, " ou "],
      [/&&/g, " et "],
      
      // Clean up multiple spaces
      [/\s+/g, " "],
    ];
    
    for (const [pattern, replacement] of replacements) {
      audioText = audioText.replace(pattern, replacement);
    }
    
    return audioText.trim();
  }, []);

  // Get text content for a block
  const getBlockText = useCallback((block) => {
    let text = "";
    if (block.title) {
      text += block.title + ". ";
    }
    if (block.question) {
      text += block.question + " ";
    }
    if (block.answer) {
      text += "Réponse : " + block.answer;
    } else if (block.text) {
      text += block.text;
    }
    
    // Transform for better audio
    return transformTextForAudio(text);
  }, [transformTextForAudio]);

  // Speak a single block (used for click-to-play)
  const speakSingleBlock = useCallback((index) => {
    if (!currentSection || !currentSection.content[index]) return;
    
    synthRef.current.cancel();
    setCurrentBlockIndex(index);
    
    const block = currentSection.content[index];
    const text = getBlockText(block);
    
    if (!text || text.trim() === '') return;
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }
    utterance.rate = speed;
    utterance.lang = 'fr-FR';
    utterance.pitch = 1;
    utterance.volume = 1;
    
    utterance.onstart = () => {
      setIsPlaying(true);
    };
    
    utterance.onend = () => {
      setIsPlaying(false);
      const progressPercent = ((index + 1) / currentSection.content.length) * 100;
      setProgress(progressPercent);
    };
    
    utterance.onerror = (e) => {
      console.error("Speech error:", e);
      setIsPlaying(false);
    };
    
    utteranceRef.current = utterance;
    
    try {
      synthRef.current.speak(utterance);
    } catch (err) {
      console.error("Speech synthesis error:", err);
      setIsPlaying(false);
    }
  }, [currentSection, selectedVoice, speed, getBlockText]);

  // Speak current block with continuous play
  const speakBlock = useCallback((index) => {
    if (!currentSection || !currentSection.content[index]) return;
    
    synthRef.current.cancel();
    
    const block = currentSection.content[index];
    const text = getBlockText(block);
    
    if (!text || text.trim() === '') {
      const nextIndex = index + 1;
      if (nextIndex < currentSection.content.length && continuousPlay) {
        setCurrentBlockIndex(nextIndex);
        setTimeout(() => speakBlock(nextIndex), 100);
      }
      return;
    }
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }
    utterance.rate = speed;
    utterance.lang = 'fr-FR';
    utterance.pitch = 1;
    utterance.volume = 1;
    
    utterance.onend = () => {
      const nextIndex = index + 1;
      if (nextIndex < currentSection.content.length && continuousPlay) {
        setCurrentBlockIndex(nextIndex);
        setTimeout(() => speakBlock(nextIndex), 300);
      } else {
        setIsPlaying(false);
        if (nextIndex >= currentSection.content.length) {
          markSectionComplete();
        }
      }
    };
    
    utterance.onerror = (e) => {
      console.error("Speech error:", e);
      const nextIndex = index + 1;
      if (nextIndex < currentSection.content.length && continuousPlay) {
        setCurrentBlockIndex(nextIndex);
        setTimeout(() => speakBlock(nextIndex), 100);
      } else {
        setIsPlaying(false);
      }
    };
    
    utteranceRef.current = utterance;
    
    try {
      synthRef.current.speak(utterance);
    } catch (err) {
      console.error("Speech synthesis error:", err);
      setIsPlaying(false);
    }
    
    const progressPercent = ((index + 1) / currentSection.content.length) * 100;
    setProgress(progressPercent);
  }, [currentSection, selectedVoice, speed, getBlockText, continuousPlay]);

  // Mark section as complete
  const markSectionComplete = async () => {
    if (!currentSection) return;
    
    try {
      await axios.post(`${API_BASE}/api/progress`, {
        section_id: currentSection.id,
        completed: true,
        last_position: currentSection.content.length - 1
      });
      setCompletedSections(prev => new Set([...prev, currentSection.id]));
    } catch (e) {
      console.error("Error saving progress:", e);
    }
  };

  // Play/Pause toggle for continuous play
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

  // Stop
  const stopPlayback = () => {
    synthRef.current.cancel();
    setIsPlaying(false);
    setCurrentBlockIndex(0);
    setProgress(0);
  };

  // Handle block click - play single block
  const handleBlockClick = (index) => {
    setContinuousPlay(false);
    speakSingleBlock(index);
  };

  // Change section
  const changeSection = (section) => {
    stopPlayback();
    setCurrentSection(section);
    setCurrentBlockIndex(0);
    setProgress(0);
    setSidebarOpen(false);
  };

  // Navigate to next/previous section
  const navigateSection = (direction) => {
    const currentIndex = course.findIndex(s => s.id === currentSection?.id);
    const newIndex = currentIndex + direction;
    if (newIndex >= 0 && newIndex < course.length) {
      changeSection(course[newIndex]);
    }
  };

  // Change speed
  const changeSpeed = (newSpeed) => {
    setSpeed(parseFloat(newSpeed));
    if (isPlaying) {
      stopPlayback();
    }
  };

  // Change voice
  const changeVoice = (voiceName) => {
    const voice = voices.find(v => v.name === voiceName);
    if (voice) {
      setSelectedVoice(voice);
      if (isPlaying) {
        stopPlayback();
      }
    }
  };

  // Get short voice name for display
  const getShortVoiceName = (voice) => {
    if (!voice) return "Voix système";
    const name = voice.name;
    if (name.includes("Google")) return name.replace("Google ", "");
    if (name.includes("Microsoft")) return name.split(" ").slice(1, 3).join(" ");
    return name.split(' ').slice(0, 2).join(' ');
  };

  // Render content block
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
        title="Cliquez pour écouter ce bloc"
      >
        <div className="block-play-indicator">
          <Volume1 size={16} />
        </div>
        {block.title && <h3 className="block-title">{block.title}</h3>}
        {block.question && <p className="qa-question">{block.question}</p>}
        {block.answer && <p className="qa-answer">{block.answer}</p>}
        {block.text && !block.answer && <p className="block-text">{block.text}</p>}
      </div>
    );
  };

  const currentSectionIndex = course.findIndex(s => s.id === currentSection?.id);
  const completionPercent = course.length > 0 ? Math.round((completedSections.size / course.length) * 100) : 0;

  return (
    <div className="app-container" data-testid="app-container">
      {/* Mobile menu button */}
      <button
        className="mobile-menu-btn"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        data-testid="mobile-menu-btn"
        aria-label="Toggle menu"
      >
        {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`} data-testid="sidebar">
        <div className="sidebar-header">
          <h1 className="font-heading text-xl font-bold text-[#0A0A0A]">
            Révision ASD
          </h1>
          <p className="font-mono text-xs text-[#4B5563] mt-1 uppercase tracking-wider">
            Titre Pro Juin 2026
          </p>
          <div className="progress-summary">
            <div className="progress-bar-small">
              <div 
                className="progress-fill-small" 
                style={{ width: `${completionPercent}%` }}
              />
            </div>
            <span className="progress-text">{completionPercent}% complété</span>
          </div>
        </div>
        
        <ScrollArea className="sidebar-nav">
          <nav>
            {course.map((section, idx) => {
              const IconComponent = iconMap[section.icon] || Brain;
              const isActive = currentSection?.id === section.id;
              const isCompleted = completedSections.has(section.id);
              
              return (
                <div
                  key={section.id}
                  data-testid={`nav-${section.id}`}
                  className={`nav-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
                  onClick={() => changeSection(section)}
                >
                  <span className="nav-number">{idx + 1}</span>
                  <IconComponent size={18} />
                  <span className="flex-1 font-body text-sm nav-title">{section.title}</span>
                  {isCompleted && <CheckCircle2 size={16} className="text-green-600" />}
                </div>
              );
            })}
          </nav>
        </ScrollArea>
      </aside>

      {/* Main content */}
      <main className="main-content" data-testid="main-content">
        <div className="content-area">
          {currentSection && (
            <>
              <div className="section-header">
                <span className="section-number">Section {currentSectionIndex + 1} / {course.length}</span>
                <h2 className="section-title" data-testid="section-title">
                  {currentSection.title}
                </h2>
                <p className="section-hint">Cliquez sur un bloc pour l'écouter</p>
              </div>
              
              <div data-testid="content-blocks">
                {currentSection.content.map((block, index) => renderBlock(block, index))}
              </div>
              
              {/* Section navigation */}
              <div className="section-nav">
                <Button
                  variant="outline"
                  onClick={() => navigateSection(-1)}
                  disabled={currentSectionIndex <= 0}
                  data-testid="prev-section-btn"
                  className="nav-btn"
                >
                  <ChevronLeft size={16} />
                  Précédent
                </Button>
                <Button
                  variant="outline"
                  onClick={() => navigateSection(1)}
                  disabled={currentSectionIndex >= course.length - 1}
                  data-testid="next-section-btn"
                  className="nav-btn"
                >
                  Suivant
                  <ChevronRight size={16} />
                </Button>
              </div>
            </>
          )}
        </div>
      </main>

      {/* Audio player */}
      <div className="audio-player" data-testid="audio-player">
        <div className="player-controls">
          <Button
            size="icon"
            variant={isPlaying ? "default" : "outline"}
            onClick={togglePlay}
            data-testid="play-pause-btn"
            aria-label={isPlaying ? "Pause" : "Lecture continue"}
            title={isPlaying ? "Arrêter" : "Lecture continue depuis ce bloc"}
            className="h-12 w-12 play-btn"
          >
            {isPlaying ? <Pause size={24} /> : <Play size={24} />}
          </Button>
          <Button
            size="icon"
            variant="outline"
            onClick={stopPlayback}
            data-testid="stop-btn"
            aria-label="Stop"
            title="Arrêter et revenir au début"
            className="h-10 w-10"
          >
            <Square size={18} />
          </Button>
        </div>

        <div className="player-info">
          <p className="player-title" data-testid="player-title">
            {currentSection?.title || "Sélectionnez une section"}
          </p>
          <p className="player-progress" data-testid="player-progress">
            Bloc {currentBlockIndex + 1} / {currentSection?.content?.length || 0}
          </p>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${progress}%` }}
              data-testid="progress-fill"
            />
          </div>
        </div>

        <div className="player-settings">
          <div className="setting-group">
            <Volume2 size={16} className="setting-icon" />
            <Select value={selectedVoice?.name || ""} onValueChange={changeVoice}>
              <SelectTrigger className="voice-select" data-testid="voice-select">
                <SelectValue placeholder={voices.length > 0 ? "Choisir voix" : "Voix par défaut"} />
              </SelectTrigger>
              <SelectContent className="z-[70]">
                {voices.length > 0 ? (
                  voices.map((voice) => (
                    <SelectItem key={voice.name} value={voice.name}>
                      {getShortVoiceName(voice)}
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="default">Voix système</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          <Select value={speed.toString()} onValueChange={changeSpeed}>
            <SelectTrigger className="speed-select" data-testid="speed-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="z-[70]">
              <SelectItem value="0.5">0.5x</SelectItem>
              <SelectItem value="0.75">0.75x</SelectItem>
              <SelectItem value="1">1x</SelectItem>
              <SelectItem value="1.25">1.25x</SelectItem>
              <SelectItem value="1.5">1.5x</SelectItem>
              <SelectItem value="2">2x</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
}

export default App;

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
  Wrench
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
    return text;
  }, []);

  // Speak current block
  const speakBlock = useCallback((index) => {
    if (!currentSection || !currentSection.content[index]) return;
    
    synthRef.current.cancel();
    
    const block = currentSection.content[index];
    const text = getBlockText(block);
    
    if (!text || text.trim() === '') {
      const nextIndex = index + 1;
      if (nextIndex < currentSection.content.length) {
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
      if (nextIndex < currentSection.content.length) {
        setCurrentBlockIndex(nextIndex);
        setTimeout(() => speakBlock(nextIndex), 300);
      } else {
        setIsPlaying(false);
        markSectionComplete();
      }
    };
    
    utterance.onerror = (e) => {
      console.error("Speech error:", e);
      const nextIndex = index + 1;
      if (nextIndex < currentSection.content.length) {
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
  }, [currentSection, selectedVoice, speed, getBlockText]);

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

  // Play/Pause toggle
  const togglePlay = () => {
    if (isPlaying) {
      synthRef.current.pause();
      setIsPlaying(false);
    } else {
      if (synthRef.current.paused) {
        synthRef.current.resume();
      } else {
        speakBlock(currentBlockIndex);
      }
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
    // Extract meaningful part of voice name
    if (name.includes("Google")) return name.replace("Google ", "");
    if (name.includes("Microsoft")) return name.split(" ").slice(1, 3).join(" ");
    return name.split(' ').slice(0, 2).join(' ');
  };

  // Render content block
  const renderBlock = (block, index) => {
    const isActive = index === currentBlockIndex && isPlaying;
    const isPast = index < currentBlockIndex;
    const blockClass = `content-block content-${block.type}`;
    
    return (
      <div
        key={index}
        data-testid={`content-block-${index}`}
        className={`${blockClass} ${isActive ? 'speech-highlight' : ''} ${isPast ? 'block-past' : ''}`}
        onClick={() => {
          setCurrentBlockIndex(index);
          if (isPlaying) {
            speakBlock(index);
          }
        }}
        style={{ cursor: 'pointer' }}
      >
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
            aria-label={isPlaying ? "Pause" : "Play"}
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

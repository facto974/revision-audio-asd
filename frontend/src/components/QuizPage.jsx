// frontend/src/components/QuizPage.jsx
import { useState, useEffect, useMemo } from "react";
import { QCM } from "../data/quizData";

const STORAGE_KEY_QCM = "asd-quiz-answers";

const loadJSON = (k, fallback) => {
  try { const s = localStorage.getItem(k); return s ? JSON.parse(s) : fallback; }
  catch { return fallback; }
};

const saveJSON = (k, v) => {
  try { localStorage.setItem(k, JSON.stringify(v)); } catch {}
};

export default function QuizPage({ onBack }) {
  const [tab, setTab] = useState("qcm");
  const [answers, setAnswers] = useState(() => loadJSON(STORAGE_KEY_QCM, {}));

  useEffect(() => saveJSON(STORAGE_KEY_QCM, answers), [answers]);

  const totals = useMemo(() => {
    const entries = Object.values(answers);
    const totalAnswered = entries.length;
    const totalCorrect = entries.filter(e => e.correct).length;
    return { totalAnswered, totalCorrect };
  }, [answers]);

  const handleAnswer = (qi, chosen) => {
    if (answers[qi] !== undefined) return;
    const correct = chosen === QCM[qi].correct;

    setAnswers(prev => ({
      ...prev,
      [qi]: { chosen, correct }
    }));
  };

  const resetAll = () => {
    if (!window.confirm("Effacer toutes tes réponses ?")) return;
    setAnswers({});
    try { localStorage.removeItem("asd-jury-revealed"); } catch {}
  };

  const progressPct = (totals.totalAnswered / QCM.length) * 100;

  return (
    <div style={S.root}>
      <div style={S.header}>
        <div style={S.headerInner}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div style={S.headerLogo}></div>
            <div>
              <h1 style={S.h1}>Entraînement Soutenance ASD</h1>
              <span style={S.h1Sub}>TopGainersCrypto — Romain RECULIN</span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <div style={S.scoreBadge}>
              Score : <span style={{ color: "#FFC000" }}>{totals.totalCorrect}/{totals.totalAnswered}</span>
            </div>

            {onBack && (
              <button onClick={onBack} style={S.resetBtn}>
                🎧 Mode audio
              </button>
            )}
          </div>
        </div>

        <div style={S.progressBar}>
          <div style={{ ...S.progressFill, width: progressPct + "%" }}></div>
        </div>
      </div>

      <div style={S.tabsWrap}>
        <div style={S.tabs}>
          <TabBtn active={tab === "qcm"} onClick={() => setTab("qcm")}>
            📝 QCM Théorique & Pratique <Badge active={tab==="qcm"}>{QCM.length}</Badge>
          </TabBtn>

          <TabBtn active={tab === "results"} onClick={() => setTab("results")}>
            📊 Résultats
          </TabBtn>
        </div>
      </div>

      <div style={S.main}>
        {tab === "qcm" && <QcmSection answers={answers} onAnswer={handleAnswer} />}
        {tab === "results" && <ResultsPanel answers={answers} onReset={resetAll} />}
      </div>
    </div>
  );
}

function TabBtn({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{ ...S.tabBtn, ...(active ? S.tabBtnActive : {}) }}>
      {children}
    </button>
  );
}

function Badge({ active, children }) {
  return (
    <span style={{ ...S.badge, ...(active ? S.badgeActive : {}) }}>{children}</span>
  );
}

function QcmSection({ answers, onAnswer }) {
  let currentSection = "";

  return (
    <>
      <ProjectPresentation />

      <div style={S.introCard}>
        <div style={{ fontSize: "1.8rem" }}>🎯</div>
        <p style={S.introText}>
          <strong style={{ color: "#FFC000" }}>Mode entraînement :</strong> clique sur une réponse pour la valider immédiatement.
        </p>
      </div>

      {QCM.map((q, i) => {
        const labels = [];

        if (q.section !== currentSection) {
          currentSection = q.section;

          const color =
            q.section.startsWith("CCP1") ? "#2E5BBA" :
            q.section.startsWith("CCP2") ? "#8E44AD" :
            q.section.startsWith("CCP3") ? "#16A085" :
            q.section.startsWith("Transversal") ? "#D35400" :
            q.section.startsWith("Bonus") ? "#34495E" :
            "#1F3864";

          labels.push(
            <div key={"sec-"+i} style={{ ...S.sectionLabel, background: color }}>
              {q.section}
            </div>
          );
        }

        return (
          <div key={i}>
            {labels}
            <QcmCard index={i} q={q} answer={answers[i]} onAnswer={onAnswer} />
          </div>
        );
      })}
    </>
  );
}

function ProjectPresentation() {
  return (
    <div style={S.briefCard}>
      <div style={S.briefHeader}>
        <div style={S.briefBadge}>📋 Présentation projet</div>
        <h2 style={S.briefTitle}>TopGainersCrypto</h2>
      </div>
    </div>
  );
}

function QcmCard({ index, q, answer, onAnswer }) {
  const answered = answer !== undefined;

  return (
    <div style={S.card}>
      <div style={S.qHeader}>
        <div style={S.qNum}>{index + 1}</div>
        <div style={S.qText}>{q.q}</div>
      </div>

      <div style={S.options}>
        {q.opts.map((opt, j) => (
          <button key={j} onClick={() => onAnswer(index, j)} disabled={answered} style={S.optionBtn}>
            <div style={S.optionLetter}>{String.fromCharCode(65 + j)}</div>
            <span>{opt}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function ResultsPanel({ answers, onReset }) {
  return (
    <div style={S.resultsPanel}>
      <button onClick={onReset} style={S.resetBtn}>
        🔄 Reset
      </button>
    </div>
  );
}

const S = {
  root: { fontFamily: "Segoe UI", padding: 20 },
  header: { background: "#1F3864", color: "white" },
  headerInner: { display: "flex", justifyContent: "space-between" },
  headerLogo: { width: 6, height: 36, background: "#ED7D31" },
  h1: { margin: 0 },
  h1Sub: { fontSize: 12 },
  scoreBadge: { fontWeight: "bold" },
  progressBar: { height: 4, background: "#ccc" },
  progressFill: { height: "100%", background: "#ED7D31" },
  tabsWrap: { background: "white" },
  tabs: { display: "flex" },
  tabBtn: { flex: 1, padding: 10 },
  tabBtnActive: { borderBottom: "3px solid #4472C4" },
  badge: {},
  badgeActive: {},
  main: { marginTop: 20 },
  card: { border: "1px solid #ccc", marginBottom: 10 },
  qHeader: { display: "flex", gap: 10 },
  qNum: { fontWeight: "bold" },
  qText: { flex: 1 },
  options: { display: "flex", flexDirection: "column" },
  optionBtn: { padding: 10 },
  optionLetter: { fontWeight: "bold" },
  resultsPanel: {},
  resetBtn: { marginTop: 10 },
  introCard: {},
  introText: {},
  sectionLabel: {},
  briefCard: {},
  briefHeader: {},
  briefBadge: {},
  briefTitle: {},
};

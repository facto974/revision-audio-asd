// frontend/src/components/QuizPage.jsx
import { useState, useEffect, useMemo } from "react";
import { QCM, JURY_QUESTIONS } from "../data/quizData";

const STORAGE_KEY_QCM  = "asd-quiz-answers";
const STORAGE_KEY_JURY = "asd-jury-revealed";

const loadJSON = (k, fallback) => {
  try { const s = localStorage.getItem(k); return s ? JSON.parse(s) : fallback; }
  catch { return fallback; }
};
const saveJSON = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } };

export default function QuizPage() {
  const [tab, setTab] = useState("qcm"); // "qcm" | "jury" | "results"
  const [answers, setAnswers] = useState(() => loadJSON(STORAGE_KEY_QCM, {}));   // { "0": {chosen: 1, correct: true}, ... }
  const [revealed, setRevealed] = useState(() => loadJSON(STORAGE_KEY_JURY, {})); // { "0": true, ... }

  useEffect(() => saveJSON(STORAGE_KEY_QCM, answers), [answers]);
  useEffect(() => saveJSON(STORAGE_KEY_JURY, revealed), [revealed]);

  const totals = useMemo(() => {
    const entries = Object.values(answers);
    const totalAnswered = entries.length;
    const totalCorrect = entries.filter(e => e.correct).length;
    return { totalAnswered, totalCorrect };
  }, [answers]);

  const handleAnswer = (qi, chosen) => {
    if (answers[qi] !== undefined) return;
    const correct = chosen === QCM[qi].correct;
    setAnswers(prev => ({ ...prev, [qi]: { chosen, correct } }));
  };

  const revealJury = (i) => setRevealed(prev => ({ ...prev, [i]: true }));

  const resetAll = () => {
    if (!window.confirm("Effacer toutes tes réponses ?")) return;
    setAnswers({}); setRevealed({});
  };

  const progressPct = (totals.totalAnswered / QCM.length) * 100;

  return (
    <div style={S.root}>
      {/* Header */}
      <div style={S.header}>
        <div style={S.headerInner}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div style={S.headerLogo}></div>
            <div>
              <h1 style={S.h1}>Entraînement Soutenance ASD</h1>
              <span style={S.h1Sub}>TopGainersCrypto — Romain RECULIN</span>
            </div>
          </div>
          <div style={S.scoreBadge}>
            Score : <span style={{ color: "#FFC000" }}>{totals.totalCorrect}/{totals.totalAnswered}</span>
          </div>
        </div>
        <div style={S.progressBar}>
          <div style={{ ...S.progressFill, width: progressPct + "%" }}></div>
        </div>
      </div>

      {/* Tabs */}
      <div style={S.tabsWrap}>
        <div style={S.tabs}>
          <TabBtn id="qcm"     active={tab === "qcm"}     onClick={() => setTab("qcm")}>📝 QCM Théorique &amp; Pratique <Badge active={tab==="qcm"}>{QCM.length}</Badge></TabBtn>
          <TabBtn id="jury"    active={tab === "jury"}    onClick={() => setTab("jury")}>🎤 Questions de Jury <Badge active={tab==="jury"}>{JURY_QUESTIONS.length}</Badge></TabBtn>
          <TabBtn id="results" active={tab === "results"} onClick={() => setTab("results")}>📊 Résultats</TabBtn>
        </div>
      </div>

      {/* Main */}
      <div style={S.main}>
        {tab === "qcm"     && <QcmSection answers={answers} onAnswer={handleAnswer} />}
        {tab === "jury"    && <JurySection revealed={revealed} onReveal={revealJury} />}
        {tab === "results" && <ResultsPanel answers={answers} onReset={resetAll} />}
      </div>
    </div>
  );
}

// ─── Sub-components ──────────────────────────────────────────────────────────

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
      <div style={S.introCard}>
        <div style={{ fontSize: "1.8rem" }}>🎯</div>
        <p style={S.introText}>
          <strong style={{ color: "#FFC000" }}>Mode entraînement :</strong> clique sur une réponse pour la valider immédiatement. L'explication apparaît pour chaque bonne ou mauvaise réponse.
        </p>
      </div>
      {QCM.map((q, i) => {
        const labels = [];
        if (q.section !== currentSection) {
          currentSection = q.section;
          const color = q.section.startsWith("03") || q.section.startsWith("05") ? "#ED7D31"
                      : q.section.startsWith("06") ? "#70AD47" : "#1F3864";
          labels.push(
            <div key={"sec-"+i} style={{ ...S.sectionLabel, background: color }}>{q.section}</div>
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

function QcmCard({ index, q, answer, onAnswer }) {
  const answered = answer !== undefined;
  const borderColor = !answered ? "#4472C4"
                    : answer.correct ? "#70AD47" : "#C00000";
  const typeStyle = q.type === "theo" ? S.tagTheo : S.tagPrat;
  const typeLabel = q.type === "theo" ? "Théorique" : "Pratique";

  return (
    <div style={{ ...S.card, borderLeftColor: borderColor }}>
      <div style={S.qHeader}>
        <div style={S.qNum}>{index + 1}</div>
        <div style={S.qText}>{q.q}</div>
        <span style={{ ...S.qTypeTag, ...typeStyle }}>{typeLabel}</span>
      </div>
      <div style={S.options}>
        {q.opts.map((opt, j) => {
          let style = { ...S.optionBtn };
          let letterStyle = { ...S.optionLetter };
          if (answered) {
            if (j === q.correct) {
              style = { ...style, ...S.optionCorrect };
              letterStyle = { ...letterStyle, background: "#70AD47", color: "white" };
            } else if (j === answer.chosen) {
              style = { ...style, ...S.optionWrong };
              letterStyle = { ...letterStyle, background: "#C00000", color: "white" };
            }
          }
          return (
            <button key={j} onClick={() => onAnswer(index, j)} disabled={answered} style={style}>
              <div style={letterStyle}>{String.fromCharCode(65 + j)}</div>
              <span>{opt}</span>
            </button>
          );
        })}
      </div>
      {answered && (
        <div style={{ ...S.explanation, ...(answer.correct ? S.expCorrect : S.expWrong) }}>
          <strong style={{ display: "block", marginBottom: "0.25rem" }}>
            {answer.correct ? "✓ Bonne réponse !" : "✗ Pas tout à fait..."}
          </strong>
          {q.exp}
        </div>
      )}
    </div>
  );
}

function JurySection({ revealed, onReveal }) {
  return (
    <>
      <div style={{ ...S.introCard, background: "#5A3010" }}>
        <div style={{ fontSize: "1.8rem" }}>🎤</div>
        <p style={S.introText}>
          <strong style={{ color: "#FFC000" }}>Simulation jury :</strong> rédige ta réponse dans le champ texte, puis clique sur "Voir la réponse modèle" pour te comparer.
        </p>
      </div>
      <div style={{ ...S.sectionLabel, background: "#ED7D31" }}>🎤 Questions types de jury ASD</div>
      {JURY_QUESTIONS.map((jq, i) => (
        <div key={i} style={{ ...S.card, borderLeftColor: "#ED7D31" }}>
          <div style={S.qHeader}>
            <div style={{ ...S.qNum, background: "#ED7D31" }}>{i + 1}</div>
            <div style={S.qText}>{jq.q}</div>
            <span style={{ ...S.qTypeTag, ...S.tagJury }}>Jury</span>
          </div>
          <div style={{ padding: "0 1.25rem 1rem" }}>
            <textarea style={S.textarea} placeholder="Écris ta réponse ici pour t'entraîner..." />
            <button style={S.revealBtn} onClick={() => onReveal(i)}>Voir la réponse modèle</button>
            {revealed[i] && (
              <div style={S.juryModel}>
                <strong style={{ color: "#ED7D31", display: "block", marginBottom: "0.3rem" }}>💡 Réponse modèle :</strong>
                {jq.model}
              </div>
            )}
          </div>
        </div>
      ))}
    </>
  );
}

function ResultsPanel({ answers, onReset }) {
  const entries = Object.entries(answers);
  const totalCorrect = entries.filter(([, v]) => v.correct).length;
  const totalAnswered = entries.length;
  const globalPct = totalAnswered > 0 ? Math.round(totalCorrect / totalAnswered * 100) : 0;

  const theoIdx = QCM.map((q, i) => ({ q, i })).filter(x => x.q.type === "theo");
  const pratIdx = QCM.map((q, i) => ({ q, i })).filter(x => x.q.type === "prat");
  const theoC = theoIdx.filter(x => answers[x.i]?.correct).length;
  const pratC = pratIdx.filter(x => answers[x.i]?.correct).length;

  const bySection = {};
  QCM.forEach((q, i) => {
    if (!bySection[q.section]) bySection[q.section] = { total: 0, correct: 0 };
    bySection[q.section].total++;
    if (answers[i]?.correct) bySection[q.section].correct++;
  });

  const rows = [
    { label: "🎯 Score global", c: totalCorrect, t: totalAnswered, color: "#4472C4" },
    { label: "📚 Théorique",   c: theoC, t: theoIdx.length, color: "#5B9BD5" },
    { label: "⚙️ Pratique",    c: pratC, t: pratIdx.length, color: "#ED7D31" },
    ...Object.entries(bySection).map(([label, d]) => ({ label, c: d.correct, t: d.total, color: "#70AD47" })),
  ];

  return (
    <div style={S.resultsPanel}>
      <div style={S.resultsTitle}>📊 Récapitulatif de tes résultats</div>
      <div style={{ marginBottom: "0.5rem", fontSize: "0.85rem", color: "#44546A" }}>
        Score global : <strong>{globalPct}%</strong>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
        {rows.map((r, i) => {
          const pct = r.t > 0 ? Math.round(r.c / r.t * 100) : 0;
          return (
            <div key={i} style={S.resultRow}>
              <div style={S.resultRowLabel}>{r.label}</div>
              <div style={S.resultBarBg}>
                <div style={{ ...S.resultBarFill, width: pct + "%", background: r.color }}></div>
              </div>
              <div style={S.resultRowScore}>{r.c}/{r.t}</div>
            </div>
          );
        })}
      </div>
      <button onClick={onReset} style={S.resetBtn}>🔄 Recommencer depuis le début</button>
    </div>
  );
}

// ─── Styles (inline pour isolation avec le reste de App.css) ────────────────
const S = {
  root: { fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif", background: "#F4F6FB", color: "#44546A", minHeight: "100vh" },
  header: { background: "#1F3864", color: "white", boxShadow: "0 2px 12px rgba(0,0,0,0.2)" },
  headerInner: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0.75rem 1.5rem", maxWidth: 900, margin: "0 auto" },
  headerLogo: { width: 6, height: 36, background: "#ED7D31", borderRadius: 3 },
  h1: { fontSize: "1rem", fontWeight: 700, lineHeight: 1.2, margin: 0 },
  h1Sub: { display: "block", fontSize: "0.72rem", fontWeight: 400, color: "#5B9BD5" },
  scoreBadge: { background: "#4472C4", padding: "0.35rem 0.9rem", borderRadius: 20, fontSize: "0.8rem", fontWeight: 700, letterSpacing: "0.5px" },
  progressBar: { height: 4, background: "rgba(255,255,255,0.15)" },
  progressFill: { height: "100%", background: "#ED7D31", transition: "width 0.4s ease" },
  tabsWrap: { background: "white", borderBottom: "2px solid #D6DCE4" },
  tabs: { display: "flex", maxWidth: 900, margin: "0 auto" },
  tabBtn: { flex: 1, padding: "0.7rem 1rem", border: "none", background: "none", cursor: "pointer", fontSize: "0.82rem", fontWeight: 600, color: "#44546A", borderBottom: "3px solid transparent", marginBottom: -2, display: "flex", alignItems: "center", justifyContent: "center", gap: "0.4rem" },
  tabBtnActive: { color: "#4472C4", borderBottom: "3px solid #4472C4", background: "#F4F6FB" },
  badge: { background: "#D6DCE4", color: "#44546A", borderRadius: 10, padding: "0.1rem 0.45rem", fontSize: "0.72rem" },
  badgeActive: { background: "#4472C4", color: "white" },
  main: { maxWidth: 900, margin: "0 auto", padding: "1.5rem" },
  introCard: { background: "#1F3864", color: "white", borderRadius: 8, padding: "1.25rem 1.5rem", marginBottom: "1.5rem", display: "flex", gap: "1rem", alignItems: "flex-start" },
  introText: { fontSize: "0.85rem", lineHeight: 1.5, color: "#C5D3E8", margin: 0 },
  sectionLabel: { display: "inline-flex", alignItems: "center", color: "white", padding: "0.3rem 0.8rem", borderRadius: 4, fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.5px", marginBottom: "1rem", textTransform: "uppercase" },
  card: { background: "white", borderRadius: 8, boxShadow: "0 2px 10px rgba(0,0,0,0.07)", marginBottom: "1.5rem", overflow: "hidden", borderLeft: "5px solid #4472C4" },
  qHeader: { padding: "1rem 1.25rem 0.5rem", display: "flex", alignItems: "flex-start", gap: "0.75rem" },
  qNum: { minWidth: 28, height: 28, borderRadius: "50%", background: "#4472C4", color: "white", fontSize: "0.75rem", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", marginTop: 2, flexShrink: 0 },
  qText: { fontSize: "0.95rem", fontWeight: 600, color: "#1F3864", lineHeight: 1.45, flex: 1 },
  qTypeTag: { fontSize: "0.68rem", fontWeight: 700, padding: "0.15rem 0.5rem", borderRadius: 3, textTransform: "uppercase", letterSpacing: "0.4px", flexShrink: 0, marginTop: 4 },
  tagTheo: { background: "#EBF1FB", color: "#4472C4" },
  tagPrat: { background: "#E8F5E1", color: "#3D7A22" },
  tagJury: { background: "#FEF0E6", color: "#ED7D31" },
  options: { padding: "0.5rem 1.25rem 1rem", display: "flex", flexDirection: "column", gap: "0.5rem" },
  optionBtn: { width: "100%", textAlign: "left", padding: "0.65rem 1rem", border: "1.5px solid #D6DCE4", borderRadius: 6, background: "white", cursor: "pointer", fontSize: "0.88rem", color: "#44546A", display: "flex", alignItems: "center", gap: "0.65rem", lineHeight: 1.35 },
  optionCorrect: { borderColor: "#70AD47", background: "#EBF6E1", color: "#2D6A12" },
  optionWrong:   { borderColor: "#C00000", background: "#FBE8E8", color: "#C00000" },
  optionLetter: { minWidth: 22, height: 22, borderRadius: "50%", background: "#D6DCE4", color: "#44546A", fontSize: "0.72rem", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 },
  explanation: { margin: "0 1.25rem 1rem", padding: "0.7rem 1rem", borderRadius: 6, fontSize: "0.85rem", lineHeight: 1.5 },
  expCorrect: { background: "#EBF6E1", borderLeft: "3px solid #70AD47", color: "#2D6A12" },
  expWrong:   { background: "#FBE8E8", borderLeft: "3px solid #C00000", color: "#8B0000" },
  textarea: { width: "100%", minHeight: 80, padding: "0.65rem 0.9rem", border: "1.5px solid #D6DCE4", borderRadius: 6, fontSize: "0.87rem", color: "#44546A", resize: "vertical", fontFamily: "inherit" },
  revealBtn: { marginTop: "0.6rem", padding: "0.5rem 1.2rem", background: "#ED7D31", color: "white", border: "none", borderRadius: 6, cursor: "pointer", fontSize: "0.82rem", fontWeight: 700 },
  juryModel: { marginTop: "0.75rem", padding: "0.75rem 1rem", background: "#FEF0E6", borderLeft: "3px solid #ED7D31", borderRadius: "0 6px 6px 0", fontSize: "0.85rem", lineHeight: 1.55, color: "#5A3010" },
  resultsPanel: { background: "white", borderRadius: 8, boxShadow: "0 2px 10px rgba(0,0,0,0.07)", padding: "1.5rem" },
  resultsTitle: { fontSize: "1.1rem", fontWeight: 700, color: "#1F3864", marginBottom: "1rem" },
  resultRow: { display: "flex", alignItems: "center", gap: "0.75rem", fontSize: "0.85rem" },
  resultRowLabel: { minWidth: 160, color: "#44546A" },
  resultBarBg: { flex: 1, height: 10, background: "#D6DCE4", borderRadius: 5, overflow: "hidden" },
  resultBarFill: { height: "100%", borderRadius: 5, transition: "width 0.6s ease" },
  resultRowScore: { minWidth: 45, textAlign: "right", fontWeight: 700, color: "#1F3864" },
  resetBtn: { padding: "0.6rem 1.5rem", background: "#4472C4", color: "white", border: "none", borderRadius: 6, cursor: "pointer", fontSize: "0.85rem", fontWeight: 700, marginTop: "1rem" },
};

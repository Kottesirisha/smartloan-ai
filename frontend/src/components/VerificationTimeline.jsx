const stages = [
  "1. Application intake",
  "2. Document upload",
  "3. Document classification",
  "4. GenAI field extraction",
  "5. Single-doc validation",
  "6. Cross-document analysis",
  "7. Kaggle ML risk scoring",
  "8. AI summary generation",
  "9. Officer review ready",
];

export default function VerificationTimeline({ currentStage = 0 }) {
  return (
    <section className="panel timeline-panel">
      <div className="section-heading">
        <h2>9-stage agentic workflow</h2>
        <p>n8n-style loan document processing pipeline.</p>
      </div>

      <div className="timeline timeline-nine">
        {stages.map((stage, index) => {
          const completed = index <= currentStage;
          const active = index === currentStage;

          return (
            <div
              className={`timeline-item ${active ? "active" : ""}`}
              key={stage}
            >
              <div
                className={`timeline-circle ${completed ? "completed" : ""}`}
              >
                {completed ? "✓" : index + 1}
              </div>
              <p className={completed ? "completed-text" : ""}>{stage}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

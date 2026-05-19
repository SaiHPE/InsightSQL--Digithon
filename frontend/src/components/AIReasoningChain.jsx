import { Check, X, Circle, Loader2 } from 'lucide-react';

const LABELS = {
  schema_grounding: 'Schema Grounding',
  sql_generation: 'SQL Generation',
  ast_validation: 'AST Validation',
  explain_check: 'EXPLAIN Check',
  execution: 'Execution',
};

const Dot = ({ status }) => {
  const cls = status === 'complete' ? 'ok' : status === 'failed' ? 'fail' : status === 'running' ? 'running' : 'pending';
  
  return (
    <div className={`step-dot ${cls}`}>
      {status === 'complete' && <Check size={12} aria-label="Complete" />}
      {status === 'failed' && <X size={12} aria-label="Failed" />}
      {status === 'running' && <Loader2 size={12} className="spinner" aria-label="Running" />}
      {status === 'pending' && <Circle size={10} aria-label="Pending" />}
    </div>
  );
};

export default function AIReasoningChain({ steps }) {
  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">AI Reasoning Chain</span>
        {steps.length > 0 && (
          <span className="badge badge-info">
            {steps.filter(s => s.status === 'complete').length}/{steps.length}
          </span>
        )}
      </div>
      <div className="section-body">
        {steps.length === 0 ? (
          <div className="empty">No active investigation</div>
        ) : (
          <div className="chain">
            {steps.map((s, i) => (
              <div key={`${s.step}-${i}`} className="step anim-in">
                <Dot status={s.status} />
                <div className="step-content">
                  <div className="step-name">{LABELS[s.step] || s.step}</div>
                  <div className="step-detail">{s.detail}</div>
                </div>
                {s.elapsed && <span className="step-time">{s.elapsed}s</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

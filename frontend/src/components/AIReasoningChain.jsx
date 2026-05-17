import { Check, X, Loader, Circle } from 'lucide-react';

const LABELS = {
  schema_grounding: 'Schema Grounding',
  sql_generation: 'SQL Generation',
  ast_validation: 'AST Validation',
  explain_check: 'EXPLAIN Check',
  execution: 'Execution',
};

const Dot = ({ status }) => {
  const cls = status === 'complete' ? 'ok' : status === 'failed' ? 'fail' : status === 'running' ? 'running' : 'pending';
  const Icon = status === 'complete' ? Check : status === 'failed' ? X : status === 'running' ? Loader : Circle;
  return <div className={`step-dot ${cls}`}><Icon size={9} /></div>;
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
                <div style={{ flex: 1, minWidth: 0 }}>
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

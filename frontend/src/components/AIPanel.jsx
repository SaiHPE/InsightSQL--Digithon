import { useState, useEffect } from 'react';
import { Brain, Search, Shield, Wrench, Check, X, Circle, Loader2, MessageSquare, Database,
         Copy, ChevronDown, ChevronRight, AlertTriangle, Zap, ChevronRight as Arrow, Info } from 'lucide-react';

/**
 * AIPanel — Tabbed investigation panel combining Reasoning, Evidence, RCA, and Actions.
 * Auto-switches tabs when new data arrives. Shows polished empty state when idle.
 *
 * HPE Design Compliance:
 *   - Tab pattern with underline indicator
 *   - Badge counts on tabs
 *   - Empty state: icon + heading + description (HPE EmptyState pattern)
 *   - Semantic status colors
 */

const STEP_LABELS = {
  schema_grounding: 'Schema Grounding',
  sql_generation: 'SQL Generation',
  ast_validation: 'AST Validation',
  explain_check: 'EXPLAIN Check',
  execution: 'Execution',
};

const STATUS_CONFIG = {
  suggested: { icon: Info, color: 'var(--status-info)', bg: 'var(--status-info-bg)', label: 'Suggested' },
  simulated: { icon: AlertTriangle, color: 'var(--status-warning)', bg: 'var(--status-warning-bg)', label: 'Simulated' },
  completed: { icon: Check, color: 'var(--status-ok)', bg: 'var(--status-ok-bg)', label: 'Completed' },
};

function StepDot({ status }) {
  const cls = status === 'complete' ? 'ok' : status === 'failed' ? 'fail' : status === 'running' ? 'running' : 'pending';
  return (
    <div className={`step-dot ${cls}`}>
      {status === 'complete' && <Check size={12} />}
      {status === 'failed' && <X size={12} />}
      {status === 'running' && <Loader2 size={12} className="spinner" />}
      {status === 'pending' && <Circle size={10} />}
    </div>
  );
}

function InvestigationTab({ steps, evidence }) {
  const [copiedId, setCopiedId] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  const handleCopy = async (sql, id) => {
    try { await navigator.clipboard.writeText(sql); setCopiedId(id); setTimeout(() => setCopiedId(null), 2000); } catch {}
  };

  return (
    <div className="ai-tab-content">
      {/* Reasoning chain */}
      {steps.length > 0 && (
        <div style={{ marginBottom: 'var(--space-md)' }}>
          <div className="ai-sub-label">Reasoning Chain
            <span className="badge badge-info" style={{ marginLeft: 'var(--space-xxs)' }}>
              {steps.filter(s => s.status === 'complete').length}/{steps.length}
            </span>
          </div>
          <div className="chain">
            {steps.map((s, i) => (
              <div key={`${s.step}-${i}`} className="step anim-in">
                <StepDot status={s.status} />
                <div className="step-content">
                  <div className="step-name">{STEP_LABELS[s.step] || s.step}</div>
                  <div className="step-detail">{s.detail}</div>
                </div>
                {s.elapsed && <span className="step-time">{s.elapsed}s</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence */}
      {evidence.length > 0 && (
        <div>
          <div className="ai-sub-label">Evidence
            <span className="badge badge-info" style={{ marginLeft: 'var(--space-xxs)' }}>{evidence.length}</span>
          </div>
          {evidence.map((e, i) => {
            const itemId = e.run_id || i;
            const hasRows = e.rows && e.rows.length > 0;
            const isExpanded = expandedId === itemId;
            return (
              <div key={itemId} className="evidence-item anim-in">
                <div className="evidence-q">
                  <MessageSquare size={14} />
                  <span>{e.question}</span>
                </div>
                <div style={{ position: 'relative' }}>
                  <div className="sql-block" style={{ maxHeight: 100, fontSize: 11 }}>{e.sql_text}</div>
                  <button type="button" className="btn btn-ghost btn-round"
                    style={{ position: 'absolute', top: 4, right: 4, width: 24, height: 24, opacity: 0.7 }}
                    onClick={() => handleCopy(e.sql_text, itemId)} aria-label="Copy SQL">
                    {copiedId === itemId ? <Check size={10} /> : <Copy size={10} />}
                  </button>
                </div>
                <div className="evidence-meta">
                  <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4xs)' }}>
                    <Database size={10} /> {e.row_count} rows
                  </span>
                  {e.elapsed && <span>{e.elapsed}s</span>}
                  {hasRows && (
                    <button type="button" className="btn btn-ghost evidence-toggle"
                      onClick={() => setExpandedId(isExpanded ? null : itemId)}
                      aria-expanded={isExpanded}>
                      {isExpanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                      {isExpanded ? 'Hide' : 'Show'}
                    </button>
                  )}
                </div>
                {isExpanded && hasRows && (
                  <div className="evidence-table-wrap">
                    <table className="evidence-table" aria-label="Query results">
                      <thead><tr>{(e.columns || Object.keys(e.rows[0])).map((c, ci) => <th key={ci}>{c}</th>)}</tr></thead>
                      <tbody>
                        {e.rows.slice(0, 6).map((row, ri) => (
                          <tr key={ri}>
                            {(e.columns || Object.keys(row)).map((c, ci) => {
                              let val = row[c];
                              if (val == null) val = '—';
                              else if (typeof val === 'number') val = Number.isInteger(val) ? val : val.toFixed(2);
                              else val = String(val).slice(0, 40);
                              return <td key={ci}>{val}</td>;
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {steps.length === 0 && evidence.length === 0 && (
        <div className="ai-empty-state">
          <Search size={28} strokeWidth={1.5} />
          <div className="ai-empty-title">No active investigation</div>
          <div className="ai-empty-desc">Investigations activate automatically when an incident is detected, or ask a question below.</div>
        </div>
      )}
    </div>
  );
}

function RCATab({ rca, actions }) {
  const data = rca?.rca;

  return (
    <div className="ai-tab-content">
      {data ? (
        <div className="anim-in">
          <div className="rca-summary-card">
            <Shield size={16} style={{ color: 'var(--hpe-green)', flexShrink: 0, marginTop: 2 }} />
            <p className="rca-summary" style={{ fontSize: 14 }}>{data.summary}</p>
          </div>

          {data.hypotheses?.map((h, i) => {
            const conf = h.confidence || 0;
            const barColor = conf >= 0.8 ? 'var(--status-critical)' : conf >= 0.5 ? 'var(--status-warning)' : 'var(--hpe-green)';
            return (
              <div key={i} className="hypothesis" style={{ borderLeft: `3px solid ${barColor}`, padding: 'var(--space-sm)' }}>
                <div className="hypothesis-header">
                  <div className="hypothesis-rank">#{i + 1}</div>
                  <div style={{ flex: 1 }}>
                    <div className="hypothesis-title" style={{ fontSize: 13 }}>{h.cause}</div>
                    <div className="conf-bar">
                      <div className="conf-track"><div className="conf-fill" style={{ width: `${conf * 100}%`, background: barColor }} /></div>
                      <span className="conf-val">{Math.round(conf * 100)}%</span>
                    </div>
                  </div>
                </div>
                {h.evidence && (
                  <div className="hypothesis-evidence" style={{ fontSize: 12 }}>
                    {h.evidence.map((ev, j) => (
                      <div key={j} className="evidence-bullet">
                        <Arrow size={10} style={{ color: 'var(--text-xweak)', flexShrink: 0, marginTop: 2 }} />
                        <span>{ev}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}

          {data.impact && (
            <div className="rca-impact" style={{ fontSize: 13 }}>
              <AlertTriangle size={14} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 2 }}>Business Impact</div>
                <div>{data.impact}</div>
              </div>
            </div>
          )}

          {data.recommended_actions?.length > 0 && (
            <div className="rca-actions" style={{ marginTop: 'var(--space-sm)' }}>
              <div className="rca-actions-title"><Zap size={12} style={{ color: 'var(--hpe-green)' }} /> Recommended Actions</div>
              {data.recommended_actions.map((a, i) => (
                <div key={i} className="rca-action" style={{ fontSize: 13 }}>
                  <span className="action-num" style={{ width: 18, height: 18, fontSize: 10 }}>{i + 1}</span>
                  <span>{a}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="ai-empty-state">
          <Shield size={28} strokeWidth={1.5} />
          <div className="ai-empty-title">Awaiting investigation</div>
          <div className="ai-empty-desc">Root cause analysis runs automatically after evidence is collected.</div>
        </div>
      )}

      {/* Remediation Actions inline */}
      {actions.length > 0 && (
        <div style={{ marginTop: 'var(--space-md)', borderTop: '1px solid var(--border-weak)', paddingTop: 'var(--space-md)' }}>
          <div className="ai-sub-label"><Wrench size={12} /> Remediation Actions
            <span className="badge badge-info" style={{ marginLeft: 'var(--space-xxs)' }}>{actions.length}</span>
          </div>
          <div className="action-list">
            {actions.map((a, i) => {
              const cfg = STATUS_CONFIG[a.status] || STATUS_CONFIG.suggested;
              const StatusIcon = cfg.icon;
              return (
                <div key={a.action_id || i} className="action-item anim-in" style={{ padding: 'var(--space-xs)' }}>
                  <div className="action-header">
                    <div className="action-type">
                      <Wrench size={12} style={{ color: 'var(--hpe-green)' }} />
                      <span style={{ fontSize: 13 }}>{(a.action_type || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                    </div>
                    <span className="action-badge" style={{ background: cfg.bg, color: cfg.color, fontSize: 10 }}>
                      <StatusIcon size={10} />{cfg.label}
                    </span>
                  </div>
                  {a.notes && <div className="action-notes" style={{ fontSize: 12 }}>{a.notes}</div>}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

const TABS = [
  { id: 'investigation', label: 'Investigation', icon: Search },
  { id: 'rca', label: 'RCA & Actions', icon: Shield },
];

export default function AIPanel({ steps, evidence, rca, actions }) {
  const [activeTab, setActiveTab] = useState('investigation');

  // Auto-switch tabs when new data arrives
  useEffect(() => {
    if (rca?.rca || actions.length > 0) setActiveTab('rca');
  }, [rca, actions.length]);

  useEffect(() => {
    if (steps.length > 0 && !rca?.rca) setActiveTab('investigation');
  }, [steps.length, rca]);

  const investigationCount = steps.length + evidence.length;
  const rcaCount = (rca?.rca ? 1 : 0) + actions.length;

  return (
    <div className="section ai-panel" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="section-head" style={{ padding: 'var(--space-xs) var(--space-md) 0' }}>
        <div className="ai-tabs">
          {TABS.map(tab => {
            const Icon = tab.icon;
            const count = tab.id === 'investigation' ? investigationCount : rcaCount;
            return (
              <button key={tab.id}
                className={`ai-tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}>
                <Icon size={14} />
                <span>{tab.label}</span>
                {count > 0 && <span className="ai-tab-badge">{count}</span>}
              </button>
            );
          })}
        </div>
      </div>
      <div className="section-body" style={{ overflowY: 'auto', flex: 1, padding: 'var(--space-sm) var(--space-md)' }}>
        {activeTab === 'investigation' && <InvestigationTab steps={steps} evidence={evidence} />}
        {activeTab === 'rca' && <RCATab rca={rca} actions={actions} />}
      </div>
    </div>
  );
}

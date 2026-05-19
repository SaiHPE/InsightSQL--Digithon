import { Check, X, Loader2, Wrench, AlertTriangle, HelpCircle } from 'lucide-react';

const ICON = {
  active: <Check size={14} aria-label="Active" />,
  failed: <X size={14} aria-label="Failed" />,
  healing: <Loader2 size={14} className="spinner" aria-label="Healing" />,
  healed: <Wrench size={14} aria-label="Healed" />,
};

const STATUS_LABEL = {
  active: (p) => `v${p.version_no || 1} active`,
  failed: () => <span style={{ color: 'var(--status-critical)' }}>FAILED</span>,
  healing: () => <span style={{ color: 'var(--status-info)' }}>Healing…</span>,
  healed: () => <span style={{ color: 'var(--hpe-green)' }}>Healed</span>,
};

export default function PanelHealth({ panels = [], healing }) {
  const healingEntries = Object.values(healing || {});

  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">Panel Health</span>
        {healingEntries.length > 0 && <span className="badge badge-info">Self-Heal Active</span>}
      </div>
      <div className="section-body">
        <div className="panel-grid">
          {panels.map((p, idx) => (
            <div key={p.panel_id} className={`ptile ${p.status === 'active' ? '' : p.status || ''} anim-in delay-${idx + 1}`}>
              <div className="ptile-name">
                {ICON[p.status] || <HelpCircle size={14} aria-label="Unknown" />} {p.panel_name}
              </div>
              <div className="ptile-status">
                {STATUS_LABEL[p.status]
                  ? STATUS_LABEL[p.status](p)
                  : <span style={{ color: 'var(--text-weak)' }}>{p.status || 'Unknown'}</span>
                }
              </div>
            </div>
          ))}
        </div>

        {healingEntries.map(h => {
          if (!h.error && !h.old_sql && !h.new_sql) return null;
          return (
            <div key={h.panel_id} className="anim-in">
              {h.error && (
                <div className="error-pill" role="alert">
                  <AlertTriangle size={14} /> Error: {h.error}
                </div>
              )}
              {h.old_sql && h.new_sql && (
                <div className="sql-diff">
                  <div>
                    <div className="diff-label old">
                      <X size={12} /> Broken SQL
                    </div>
                    <div className="sql-block old-sql">{h.old_sql}</div>
                  </div>
                  <div>
                    <div className="diff-label new">
                      <Check size={12} /> Healed SQL
                    </div>
                    <div className="sql-block new-sql">{h.new_sql}</div>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {panels.length === 0 && <div className="empty">Loading panels…</div>}
      </div>
    </div>
  );
}

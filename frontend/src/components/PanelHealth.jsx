import { Check, X, Loader2, Wrench, AlertTriangle } from 'lucide-react';

const ICON = { 
  active: <Check size={14} aria-label="Active" />, 
  failed: <X size={14} aria-label="Failed" />, 
  healing: <Loader2 size={14} className="spinner" aria-label="Healing" />, 
  healed: <Wrench size={14} aria-label="Healed" /> 
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
                {ICON[p.status] || ICON.active} {p.panel_name}
              </div>
              <div className="ptile-status">
                {p.status === 'active' && `v${p.version_no || 1} active`}
                {p.status === 'failed' && <span style={{ color: 'var(--status-critical)' }}>FAILED</span>}
                {p.status === 'healing' && <span style={{ color: 'var(--status-info)' }}>Healing…</span>}
                {p.status === 'healed' && <span style={{ color: 'var(--hpe-green)' }}>Healed</span>}
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

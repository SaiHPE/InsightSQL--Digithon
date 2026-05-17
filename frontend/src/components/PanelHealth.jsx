import { Check, X, Loader, Wrench } from 'lucide-react';

const ICON = { active: <Check size={11} />, failed: <X size={11} />, healing: <Loader size={11} />, healed: <Wrench size={11} /> };

export default function PanelHealth({ panels = [], healing }) {
  const healingEntries = Object.values(healing || {});

  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">Panel Health</span>
        {healingEntries.length > 0 && <span className="badge badge-heal">Self-Heal Active</span>}
      </div>
      <div className="section-body">
        <div className="panel-grid">
          {panels.map(p => (
            <div key={p.panel_id} className={`ptile ${p.status === 'active' ? '' : p.status || ''}`}>
              <div className="ptile-name">
                {ICON[p.status] || ICON.active} {p.panel_name}
              </div>
              <div className="ptile-status" style={{
                color: p.status === 'failed' ? 'var(--crit)' :
                       p.status === 'healed' ? 'var(--jade)' :
                       p.status === 'healing' ? 'var(--heal)' : 'var(--t3)',
              }}>
                {p.status === 'active' && `v${p.version_no || 1} active`}
                {p.status === 'failed' && 'FAILED'}
                {p.status === 'healing' && 'Healing…'}
                {p.status === 'healed' && 'Healed ✓'}
              </div>
            </div>
          ))}
        </div>

        {healingEntries.map(h => {
          if (!h.error && !h.old_sql && !h.new_sql) return null;
          return (
            <div key={h.panel_id} className="anim-in">
              {h.error && <div className="error-pill">Error: {h.error}</div>}
              {h.old_sql && h.new_sql && (
                <div className="sql-diff">
                  <div>
                    <div className="diff-label old">Broken SQL</div>
                    <div className="sql-block old-sql">{h.old_sql}</div>
                  </div>
                  <div>
                    <div className="diff-label new">Healed SQL</div>
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

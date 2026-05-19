import { Check, X, Loader2, Wrench, AlertTriangle, HelpCircle } from 'lucide-react';

/**
 * PanelHealth — Dashboard panel health monitor with step-by-step healing progress.
 * Shows panel grid + healing reasoning chain + SQL diff.
 *
 * HPE Design Compliance:
 *   - Status colors: ok/warning/critical/info via HPE semantic tokens
 *   - Card tiles with left-border color indicator (HPE status pattern)
 *   - Step reasoning chain reuses step-dot CSS classes
 *   - Accessible: role="alert" on errors, aria-label on status badges
 */

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

const HEAL_STEP_LABELS = {
  loading: 'Loading Panel',
  diagnosing: 'Diagnosing Error',
  schema_lookup: 'Schema Lookup',
  generating_fix: 'Generating Fix',
  validating_fix: 'Validating Fix',
  promoting: 'Promoting Version',
};

function HealStepChain({ steps = [] }) {
  if (steps.length === 0) return null;
  return (
    <div className="heal-chain">
      {steps.map((s, i) => {
        const cls = s.status === 'complete' ? 'ok' : s.status === 'failed' ? 'fail' : s.status === 'running' ? 'running' : 'pending';
        return (
          <div key={s.step || i} className="step heal-step anim-in">
            <div className={`step-dot ${cls}`}>
              {s.status === 'complete' && <Check size={10} />}
              {s.status === 'failed' && <X size={10} />}
              {s.status === 'running' && <Loader2 size={10} className="spinner" />}
            </div>
            {i < steps.length - 1 && <div className="elog-line" style={{ left: 9, top: 24, bottom: -4 }} />}
            <div className="step-content">
              <div className="step-name" style={{ fontSize: 13 }}>{HEAL_STEP_LABELS[s.step] || s.step}</div>
              {s.detail && <div className="step-detail">{s.detail}</div>}
            </div>
            {s.elapsed && <span className="step-time">{s.elapsed}s</span>}
          </div>
        );
      })}
    </div>
  );
}

export default function PanelHealth({ panels = [], healing }) {
  const healingEntries = Object.values(healing || {});
  const allHealthy = panels.length > 0 && panels.every(p => p.status === 'active');
  const hasActivity = healingEntries.length > 0 || !allHealthy;

  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">Panel Health</span>
        {allHealthy && <span className="badge badge-ok">{panels.length}/{panels.length} healthy ✓</span>}
        {healingEntries.some(h => h.status === 'healed') && <span className="badge badge-ok">Self-Healed</span>}
        {healingEntries.some(h => h.steps?.some(s => s.status === 'running')) && <span className="badge badge-info">Healing…</span>}
      </div>
      <div className="section-body">
        {/* Only show full grid when there's something interesting */}
        {(hasActivity || panels.length === 0) && (
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
        )}

        {/* Healing step-by-step progress */}
        {healingEntries.map(h => {
          if (!h.steps?.length && !h.error && !h.old_sql) return null;
          return (
            <div key={h.panel_id} className="heal-detail anim-in">
              {/* Step progress chain */}
              {h.steps?.length > 0 && (
                <div className="heal-steps-section">
                  <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-weak)', marginBottom: 'var(--space-xxs)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Healing Progress
                  </div>
                  <HealStepChain steps={h.steps} />
                </div>
              )}

              {h.error && !h.new_sql && (
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

              {h.error_fixed && h.status === 'healed' && (
                <div style={{ marginTop: 'var(--space-sm)', padding: 'var(--space-sm)', background: 'var(--status-ok-bg)', borderRadius: 'var(--radius-sm)', fontSize: 13, color: 'var(--status-ok)' }}>
                  <Check size={14} style={{ verticalAlign: 'middle', marginRight: 'var(--space-4xs)' }} />
                  Fixed: {h.error_fixed}{h.shadow_rows != null ? ` • Shadow-run verified (${h.shadow_rows} rows)` : ''}{h.elapsed != null ? ` • Promoted in ${h.elapsed}s` : ''}
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

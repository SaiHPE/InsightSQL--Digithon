import { Wrench, CheckCircle, AlertTriangle, Info, ArrowRight } from 'lucide-react';

/**
 * ActionPanel — Shows remediation actions suggested by InsightSQL.
 * Displays action type, target resource, status, and notes.
 *
 * HPE Design Compliance:
 *   - Status badges use HPE semantic status colors
 *   - Card surface pattern with section-head/section-body
 *   - T-Shirt spacing
 *   - Accessible: status badges have aria-label
 */

const STATUS_CONFIG = {
  suggested:  { icon: Info,          color: 'var(--status-info)',     bg: 'var(--status-info-bg)',     label: 'Suggested' },
  simulated:  { icon: AlertTriangle, color: 'var(--status-warning)', bg: 'var(--status-warning-bg)',  label: 'Simulated' },
  completed:  { icon: CheckCircle,   color: 'var(--status-ok)',      bg: 'var(--status-ok-bg)',       label: 'Completed' },
};

function formatActionType(type) {
  return (type || 'unknown')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function formatResource(id) {
  if (!id) return '—';
  // e.g. "sap_sid:PRD" → "SAP SID PRD"
  return id.replace(':', ' ').replace(/_/g, ' ').toUpperCase();
}

export default function ActionPanel({ actions = [] }) {
  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">Remediation Actions</span>
        {actions.length > 0 && (
          <span className="badge badge-info">{actions.length}</span>
        )}
      </div>
      <div className="section-body">
        {actions.length === 0 ? (
          <div className="empty">No actions suggested yet</div>
        ) : (
          <div className="action-list">
            {actions.map((a, i) => {
              const cfg = STATUS_CONFIG[a.status] || STATUS_CONFIG.suggested;
              const StatusIcon = cfg.icon;
              return (
                <div key={a.action_id || i} className="action-item anim-in">
                  <div className="action-header">
                    <div className="action-type">
                      <Wrench size={14} style={{ color: 'var(--hpe-green)' }} aria-hidden="true" />
                      <span>{formatActionType(a.action_type)}</span>
                    </div>
                    <span
                      className="action-badge"
                      style={{ background: cfg.bg, color: cfg.color }}
                      aria-label={`Status: ${cfg.label}`}
                    >
                      <StatusIcon size={12} />
                      {cfg.label}
                    </span>
                  </div>
                  <div className="action-target">
                    <ArrowRight size={12} style={{ color: 'var(--text-xweak)' }} aria-hidden="true" />
                    <span>{formatResource(a.target_resource_id)}</span>
                  </div>
                  {a.notes && <div className="action-notes">{a.notes}</div>}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

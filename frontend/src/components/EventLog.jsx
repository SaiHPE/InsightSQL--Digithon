import { useEffect, useRef } from 'react';
import {
  AlertCircle, Activity, Database, Brain,
  Wrench, Cpu, HardDrive, Search, Zap,
} from 'lucide-react';

/**
 * EventLog — Chronological event timeline showing all system activity.
 * Consolidates alerts, metrics, investigations, RCA, and panel events into
 * a single "story view" so judges can follow the narrative.
 *
 * HPE Design Compliance:
 *   - Uses HPE semantic status colors for severity
 *   - T-Shirt spacing scale
 *   - Accessible: aria-label on icons, role="log"
 *   - HPE Graphik typography
 */

const TYPE_CONFIG = {
  alert:         { icon: AlertCircle, color: 'var(--status-critical)' },
  metric_spike:  { icon: Activity,    color: 'var(--status-warning)' },
  investigation: { icon: Search,      color: 'var(--status-info)' },
  evidence:      { icon: Database,    color: 'var(--graph-2)' },
  rca:           { icon: Brain,       color: 'var(--graph-3)' },
  panel_fail:    { icon: Zap,         color: 'var(--status-critical)' },
  panel_heal:    { icon: Wrench,      color: 'var(--hpe-green)' },
  compute:       { icon: Cpu,         color: 'var(--graph-4)' },
  storage:       { icon: HardDrive,   color: 'var(--graph-1)' },
  remediation:   { icon: Wrench,      color: 'var(--status-info)' },
  default:       { icon: Activity,    color: 'var(--text-weak)' },
};

function formatTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    const diff = Math.round((Date.now() - d.getTime()) / 1000);
    if (diff < 5) return 'just now';
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
  } catch { return ''; }
}

export default function EventLog({ events = [] }) {
  const scrollRef = useRef(null);

  // Auto-scroll to latest
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  return (
    <div className="section" style={{ maxHeight: 420, display: 'flex', flexDirection: 'column' }}>
      <div className="section-head">
        <span className="section-title">Event Log</span>
        {events.length > 0 && (
          <span className="badge badge-info">{events.length}</span>
        )}
      </div>
      <div
        className="section-body event-log-body"
        ref={scrollRef}
        role="log"
        aria-label="System event log"
        style={{ overflowY: 'auto', flex: 1, padding: 'var(--space-sm) var(--space-md)' }}
      >
        {events.length === 0 ? (
          <div className="empty" style={{ padding: 'var(--space-lg) 0' }}>Waiting for events…</div>
        ) : (
          events.map((ev, i) => {
            const cfg = TYPE_CONFIG[ev.type] || TYPE_CONFIG.default;
            const Icon = cfg.icon;
            return (
              <div key={i} className="elog-entry anim-in">
                <div className="elog-dot" style={{ borderColor: cfg.color, color: cfg.color }}>
                  <Icon size={10} aria-label={ev.type} />
                </div>
                {i < events.length - 1 && <div className="elog-line" />}
                <div className="elog-content">
                  <span className="elog-text">{ev.summary}</span>
                  <span className="elog-time">{formatTime(ev.ts)}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

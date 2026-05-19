import { useState, useEffect } from 'react';
import { AlertCircle } from 'lucide-react';

export default function IncidentBanner({ incident, rca }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    setElapsed(0);
    const t = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(t);
  }, [incident?.incident_id]);

  const impact = Math.round((elapsed / 60) * (incident.impact_per_min_usd || 0));
  const confidence = rca?.confidence != null ? Math.round(rca.confidence * 100) : null;

  // Map backend severity to HPE Status tokens
  const sevClass = incident.severity === 'warning' ? 'warn' : 'crit';

  return (
    <div className="banner anim-in" role="alert" aria-live="polite">
      <div className="banner-left">
        {/* HPE Status 3-of-4 Rule: Color, Icon, Shape(Badge), Content */}
        <span className={`badge badge-${sevClass}`}>
          <AlertCircle size={14} aria-hidden="true" />
          {incident.severity || 'critical'}
        </span>
        <span className="banner-title">{incident.title}</span>
      </div>

      <div className="banner-right">
        {confidence != null && <span>Confidence: <strong>{confidence}%</strong></span>}
        <span className="impact-value">Impact: ${impact.toLocaleString()}</span>
        <span>Duration: {Math.floor(elapsed / 60)}m {elapsed % 60}s</span>
      </div>
    </div>
  );
}

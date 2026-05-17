import { useState, useEffect } from 'react';

export default function IncidentBanner({ incident, rca }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    setElapsed(0);
    const t = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(t);
  }, [incident?.incident_id]);

  const impact = Math.round((elapsed / 60) * (incident.impact_per_min_usd || 11800));
  const confidence = rca?.confidence ? Math.round(rca.confidence * 100) : null;

  return (
    <div className="banner anim-in">
      <div className="banner-left">
        <span className="badge badge-crit">{incident.severity || 'critical'}</span>
        <span className="banner-title">{incident.title}</span>
      </div>
      <div className="banner-right">
        {confidence && <span>Confidence: {confidence}%</span>}
        <span className="impact-value">Impact: ${impact.toLocaleString()}</span>
        <span>{Math.floor(elapsed / 60)}m {elapsed % 60}s</span>
      </div>
    </div>
  );
}

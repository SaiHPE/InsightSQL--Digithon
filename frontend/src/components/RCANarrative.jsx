import { Shield, AlertTriangle, Zap, ChevronRight } from 'lucide-react';

/**
 * RCANarrative — Root cause analysis display with improved readability.
 * HPE Design: large summary, confidence-colored hypothesis cards,
 * warning alert for impact, numbered actions with green accents.
 */
export default function RCANarrative({ rca }) {
  const data = rca?.rca;

  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">Root Cause Analysis</span>
        {rca?.confidence && <span className="badge badge-ok">{Math.round(rca.confidence * 100)}%</span>}
      </div>
      <div className="section-body">
        {!data ? (
          <div className="empty">Awaiting investigation…</div>
        ) : (
          <div className="anim-in">
            <div className="rca-summary-card">
              <Shield size={18} style={{ color: 'var(--hpe-green)', flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
              <p className="rca-summary">{data.summary}</p>
            </div>

            {data.hypotheses?.map((h, i) => {
              const conf = h.confidence || 0;
              const barColor = conf >= 0.8 ? 'var(--status-critical)' : conf >= 0.5 ? 'var(--status-warning)' : 'var(--hpe-green)';
              return (
                <div key={i} className="hypothesis" style={{ borderLeft: `3px solid ${barColor}` }}>
                  <div className="hypothesis-header">
                    <div className="hypothesis-rank">#{i + 1}</div>
                    <div style={{ flex: 1 }}>
                      <div className="hypothesis-title">{h.cause}</div>
                      <div className="conf-bar">
                        <div className="conf-track">
                          <div className="conf-fill" style={{ width: `${conf * 100}%`, background: barColor }} />
                        </div>
                        <span className="conf-val">{Math.round(conf * 100)}%</span>
                      </div>
                    </div>
                  </div>
                  {h.evidence && (
                    <div className="hypothesis-evidence">
                      {h.evidence.map((ev, j) => (
                        <div key={j} className="evidence-bullet">
                          <ChevronRight size={12} style={{ color: 'var(--text-xweak)', flexShrink: 0, marginTop: 2 }} />
                          <span>{ev}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}

            {data.impact && (
              <div className="rca-impact">
                <AlertTriangle size={16} aria-hidden="true" />
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>Business Impact</div>
                  <div>{data.impact}</div>
                </div>
              </div>
            )}

            {data.recommended_actions?.length > 0 && (
              <div className="rca-actions">
                <div className="rca-actions-title">
                  <Zap size={14} style={{ color: 'var(--hpe-green)' }} /> Recommended Actions
                </div>
                {data.recommended_actions.map((a, i) => (
                  <div key={i} className="rca-action">
                    <span className="action-num">{i + 1}</span>
                    <span>{a}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

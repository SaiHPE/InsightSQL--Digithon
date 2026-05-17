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
          <>
            <p className="rca-summary">{data.summary}</p>

            {data.hypotheses?.map((h, i) => (
              <div key={i} className="hypothesis">
                <div className="hypothesis-title">{i + 1}. {h.cause}</div>
                <div className="conf-bar">
                  <div className="conf-track">
                    <div className="conf-fill" style={{ width: `${(h.confidence || 0) * 100}%` }} />
                  </div>
                  <span className="conf-val">{Math.round((h.confidence || 0) * 100)}%</span>
                </div>
                {h.evidence && (
                  <div className="hypothesis-evidence">
                    {h.evidence.map((ev, j) => <div key={j}>• {ev}</div>)}
                  </div>
                )}
              </div>
            ))}

            {data.impact && <div className="rca-impact"><strong>Impact:</strong> {data.impact}</div>}

            {data.recommended_actions?.length > 0 && (
              <div className="rca-actions">
                <div className="rca-actions-title">Recommended Actions</div>
                {data.recommended_actions.map((a, i) => (
                  <div key={i} className="rca-action">→ {a}</div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

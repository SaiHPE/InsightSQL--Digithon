import { MessageSquare, Database } from 'lucide-react';

export default function EvidencePanel({ evidence }) {
  return (
    <div className="section" style={{ maxHeight: 480, display: 'flex', flexDirection: 'column' }}>
      <div className="section-head">
        <span className="section-title">Evidence</span>
        {evidence.length > 0 && <span className="badge badge-info">{evidence.length} queries</span>}
      </div>
      <div className="section-body" style={{ overflowY: 'auto', flex: 1 }}>
        {evidence.length === 0 ? (
          <div className="empty">No evidence collected yet</div>
        ) : (
          evidence.map((e, i) => (
            <div key={e.run_id || i} className="evidence-item anim-in">
              <div className="evidence-q">
                <MessageSquare size={13} />
                {e.question}
              </div>
              <div className="sql-block">{e.sql_text}</div>
              <div className="evidence-meta">
                <span><Database size={11} style={{ verticalAlign: -1 }} /> {e.row_count} rows</span>
                {e.elapsed && <span>{e.elapsed}s</span>}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

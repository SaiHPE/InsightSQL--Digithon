import { MessageSquare, Database, Copy } from 'lucide-react';

export default function EvidencePanel({ evidence }) {
  const handleCopy = (sql) => {
    navigator.clipboard.writeText(sql);
  };

  return (
    <div className="section" style={{ maxHeight: 480, display: 'flex', flexDirection: 'column' }}>
      <div className="section-head">
        <span className="section-title">Evidence</span>
        {evidence.length > 0 && <span className="badge badge-info">{evidence.length} queries</span>}
      </div>
      <div className="section-body" style={{ overflowY: 'auto', flex: 1, padding: 'var(--space-md)' }}>
        {evidence.length === 0 ? (
          <div className="empty">No evidence collected yet</div>
        ) : (
          evidence.map((e, i) => (
            <div key={e.run_id || i} className="evidence-item anim-in">
              <div className="evidence-q">
                <MessageSquare size={16} />
                <span>{e.question}</span>
              </div>
              <div style={{ position: 'relative' }}>
                <div className="sql-block">{e.sql_text}</div>
                <button 
                  className="btn btn-ghost btn-round" 
                  style={{ position: 'absolute', top: 4, right: 4, width: 28, height: 28, opacity: 0.7 }}
                  onClick={() => handleCopy(e.sql_text)}
                  title="Copy SQL"
                >
                  <Copy size={12} />
                </button>
              </div>
              <div className="evidence-meta">
                <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4xs)' }}>
                  <Database size={12} /> {e.row_count} rows
                </span>
                {e.elapsed && <span>{e.elapsed}s</span>}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

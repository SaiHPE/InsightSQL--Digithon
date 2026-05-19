import { useState } from 'react';
import { MessageSquare, Database, Copy, Check, ChevronDown, ChevronRight } from 'lucide-react';

/**
 * EvidencePanel — Shows collected evidence from Text-to-SQL investigations.
 * Now includes expandable result rows table for evidence transparency.
 *
 * HPE Design Compliance:
 *   - Section card pattern (section-head / section-body)
 *   - Monospace font for SQL blocks
 *   - Table uses HPE-styled alternating rows
 *   - Copy-to-clipboard with accessible labeling
 *   - T-Shirt spacing
 */

function MiniTable({ columns, rows }) {
  if (!rows || rows.length === 0) return null;
  // Use column names from data keys if columns not provided
  const cols = columns || (rows[0] ? Object.keys(rows[0]) : []);

  return (
    <div className="evidence-table-wrap">
      <table className="evidence-table" aria-label="Query results">
        <thead>
          <tr>
            {cols.map((c, i) => <th key={i}>{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 8).map((row, ri) => (
            <tr key={ri}>
              {cols.map((c, ci) => {
                let val = row[c];
                if (val === null || val === undefined) val = '—';
                else if (typeof val === 'number') val = Number.isInteger(val) ? val : val.toFixed(2);
                else if (typeof val === 'object') val = JSON.stringify(val).slice(0, 60);
                else val = String(val).slice(0, 60);
                return <td key={ci}>{val}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 8 && (
        <div style={{ fontSize: 11, color: 'var(--text-xweak)', textAlign: 'center', marginTop: 'var(--space-4xs)' }}>
          +{rows.length - 8} more rows
        </div>
      )}
    </div>
  );
}

export default function EvidencePanel({ evidence }) {
  const [copiedId, setCopiedId] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  const handleCopy = async (sql, id) => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy SQL:', err);
    }
  };

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="section" style={{ maxHeight: 560, display: 'flex', flexDirection: 'column' }}>
      <div className="section-head">
        <span className="section-title">Evidence</span>
        {evidence.length > 0 && <span className="badge badge-info">{evidence.length} queries</span>}
      </div>
      <div className="section-body" style={{ overflowY: 'auto', flex: 1, padding: 'var(--space-md)' }}>
        {evidence.length === 0 ? (
          <div className="empty">No evidence collected yet</div>
        ) : (
          evidence.map((e, i) => {
            const itemId = e.run_id || i;
            const hasRows = e.rows && e.rows.length > 0;
            const isExpanded = expandedId === itemId;
            return (
              <div key={itemId} className="evidence-item anim-in">
                <div className="evidence-q">
                  <MessageSquare size={16} />
                  <span>{e.question}</span>
                </div>
                <div style={{ position: 'relative' }}>
                  <div className="sql-block">{e.sql_text}</div>
                  <button
                    type="button"
                    className="btn btn-ghost btn-round"
                    style={{ position: 'absolute', top: 4, right: 4, width: 28, height: 28, opacity: 0.7 }}
                    onClick={() => handleCopy(e.sql_text, itemId)}
                    aria-label="Copy SQL to clipboard"
                  >
                    {copiedId === itemId ? <Check size={12} /> : <Copy size={12} />}
                  </button>
                </div>
                <div className="evidence-meta">
                  <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4xs)' }}>
                    <Database size={12} /> {e.row_count} rows
                  </span>
                  {e.elapsed && <span>{e.elapsed}s</span>}
                  {hasRows && (
                    <button
                      type="button"
                      className="btn btn-ghost evidence-toggle"
                      onClick={() => toggleExpand(itemId)}
                      aria-expanded={isExpanded}
                      aria-label={isExpanded ? 'Hide results' : 'Show results'}
                    >
                      {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                      {isExpanded ? 'Hide Results' : 'Show Results'}
                    </button>
                  )}
                </div>
                {isExpanded && hasRows && (
                  <MiniTable columns={e.columns} rows={e.rows} />
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

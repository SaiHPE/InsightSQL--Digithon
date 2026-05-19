import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, MessageSquare } from 'lucide-react';

/**
 * ChatInput — Ad-hoc Text-to-SQL input bar.
 * Allows judges to type natural-language questions that trigger live AI investigation.
 * POSTs to /api/incidents/{incident_id}/ask
 *
 * HPE Design Compliance:
 *   - Uses --bg-input token for input field
 *   - btn-primary for send action (HPE CTA pattern)
 *   - Focus ring via :focus-visible
 *   - Accessible: aria-label, role, disabled states
 *   - T-Shirt spacing
 */

const EXAMPLE_QUESTIONS = [
  'Which volume has the highest latency right now?',
  'Was a backup running during the SAP slowdown?',
  'Show host temperature and CPU for the last 15 minutes',
  'What is the storage saturation score on primera-prod-01?',
];

export default function ChatInput({ incidentId, isInvestigating }) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const apiBase = import.meta.env.VITE_API_URL || window.location.origin;

  // Cycle through placeholder examples
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setPlaceholderIdx(i => (i + 1) % EXAMPLE_QUESTIONS.length), 4000);
    return () => clearInterval(t);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const q = query.trim();
    if (!q || !incidentId || loading) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/incidents/${encodeURIComponent(incidentId)}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed: ${res.status}`);
      }
      setQuery('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const disabled = !incidentId || loading || isInvestigating;

  return (
    <div className="chat-input-wrapper">
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <div className="chat-input-icon" aria-hidden="true">
          <MessageSquare size={16} />
        </div>
        <input
          ref={inputRef}
          type="text"
          className="chat-input"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={incidentId ? EXAMPLE_QUESTIONS[placeholderIdx] : 'Start a demo to ask questions…'}
          disabled={disabled}
          aria-label="Ask a natural language question for Text-to-SQL investigation"
        />
        <button
          type="submit"
          className="btn btn-primary chat-send"
          disabled={disabled || !query.trim()}
          aria-label="Send question"
        >
          {loading ? <Loader2 size={16} className="spinner" /> : <Send size={16} />}
        </button>
      </form>
      {error && (
        <div className="chat-error" role="alert">{error}</div>
      )}
    </div>
  );
}

import { useState, useRef, useEffect } from 'react';
import { Zap, RotateCcw, ChevronDown, ChevronUp, Loader2, Check } from 'lucide-react';

const INCIDENTS = [
  { num: 1, label: 'SAP Slowdown', desc: 'Storage I/O contention from HANA backup' },
  { num: 2, label: 'Compute', desc: 'Host thermal throttling on prd-hana-02' },
  { num: 3, label: 'Self-Heal', desc: 'Dashboard panel SQL auto-repair' },
  { num: 4, label: 'Capacity', desc: 'Storage capacity forecast breach' },
];

export default function DemoControl({ demo }) {
  const [open, setOpen] = useState(true);
  const [running, setRunning] = useState(null);
  const [completed, setCompleted] = useState(new Set());
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState(null);
  const apiBase = import.meta.env.VITE_API_URL || window.location.origin;
  const pollRef = useRef(null);

  // Sync completed state from server on mount (handles page refresh mid-demo)
  useEffect(() => {
    fetch(`${apiBase}/api/demo/status`)
      .then(r => r.json())
      .then(data => {
        if (data.completed?.length) setCompleted(new Set(data.completed));
        if (data.running) setRunning(null); // don't try to re-track a running incident
      })
      .catch(() => {});
  }, [apiBase]);

  // Clear polling interval on unmount to prevent memory leak
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const triggerIncident = async (num) => {
    setRunning(num);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/demo/incident/${num}`, { method: 'POST' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Incident ${num} failed: ${res.status}`);
      }
      // Poll until done (check every 2s)
      pollRef.current = setInterval(async () => {
        try {
          const status = await fetch(`${apiBase}/api/demo/status`);
          const data = await status.json();
          if (!data.running) {
            clearInterval(pollRef.current);
            pollRef.current = null;
            setRunning(null);
            setCompleted(new Set(data.completed || []));
          }
        } catch { /* ignore poll errors */ }
      }, 2000);
    } catch (e) {
      console.error('[Demo]', e);
      setError(e.message);
      setRunning(null);
    }
  };

  const reset = async () => {
    setResetting(true);
    setError(null);
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    try {
      const res = await fetch(`${apiBase}/api/demo/reset`, { method: 'POST' });
      if (!res.ok) throw new Error(`Reset failed: ${res.status}`);
      setCompleted(new Set());
      setRunning(null);
      window.location.reload();
    } catch (e) {
      console.error('[Demo]', e);
      setError(e.message);
    } finally {
      setResetting(false);
    }
  };

  const isBusy = running !== null || resetting;

  return (
    <div className="demo-dock">
      {open && (
        <div className="demo-panel anim-in">
          <div className="demo-grid">
            {INCIDENTS.map(inc => {
              const isDone = completed.has(inc.num);
              const isRunning = running === inc.num;
              return (
                <button
                  key={inc.num}
                  className={`demo-trigger ${isDone ? 'done' : ''} ${isRunning ? 'active' : ''}`}
                  onClick={() => triggerIncident(inc.num)}
                  disabled={isBusy || isDone}
                  title={inc.desc}
                >
                  <span className="demo-trigger-num">
                    {isRunning ? <Loader2 size={14} className="spinner" /> :
                     isDone ? <Check size={14} /> :
                     inc.num}
                  </span>
                  <span className="demo-trigger-label">{inc.label}</span>
                </button>
              );
            })}
          </div>
          <button className="btn btn-ghost demo-reset" onClick={reset} disabled={isBusy}>
            <RotateCcw size={14} /> Reset
          </button>
          {/* Phase info + talking point shown during active incident */}
          {demo.phase !== 'idle' && demo.phase !== 'complete' && (
            <div className="demo-status anim-in">
              <div className="demo-title">{demo.title}</div>
              {demo.talkingPoint && (
                <div className="demo-talk">"{demo.talkingPoint}"</div>
              )}
            </div>
          )}
          {error && <div style={{ color: 'var(--status-critical)', fontSize: 12, marginTop: 'var(--space-xxs)' }}>{error}</div>}
        </div>
      )}
      <button
        className="btn btn-round"
        onClick={() => setOpen(!open)}
        aria-label={open ? 'Close Demo Panel' : 'Open Demo Panel'}
      >
        {open ? <ChevronDown size={20} /> : <ChevronUp size={20} />}
      </button>
    </div>
  );
}

import { useState } from 'react';
import { Play, RotateCcw, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';

export default function DemoControl({ demo }) {
  const [open, setOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const apiBase = import.meta.env.VITE_API_URL || window.location.origin;

  const start = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/demo/start`, { method: 'POST' });
      if (!res.ok) throw new Error(`Demo start failed: ${res.status}`);
    } catch (e) {
      console.error('[Demo]', e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const reset = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/demo/reset`, { method: 'POST' });
      if (!res.ok) throw new Error(`Demo reset failed: ${res.status}`);
      window.location.reload();
    } catch (e) {
      console.error('[Demo]', e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const running = demo.phase !== 'idle' && demo.phase !== 'complete';

  return (
    <div className="demo-dock">
      {open && (
        <div className="demo-panel anim-in">
          <div className="demo-btns">
            <button className="btn btn-primary" onClick={start} disabled={loading || running}>
              {loading || running ? <Loader2 size={16} className="spinner" /> : <Play size={16} />}
              {running ? 'Running…' : 'Run Demo'}
            </button>
            <button className="btn btn-ghost" onClick={reset} disabled={loading}>
              <RotateCcw size={16} /> Reset
            </button>
          </div>
          {demo.phase !== 'idle' && (
            <div className="anim-in">
              <div className="demo-title">
                {demo.phaseNumber > 0 && (
                  <span style={{ color: 'var(--hpe-green)' }}>
                    {`${'●'.repeat(demo.phaseNumber)}${'○'.repeat(Math.max(0, 3 - demo.phaseNumber))} `}
                  </span>
                )}
                {demo.title}
              </div>
              <div className="demo-talk">"{demo.talkingPoint}"</div>
            </div>
          )}
          {error && <div style={{ color: 'var(--status-critical)', fontSize: 12, marginTop: 'var(--space-xxs)' }}>{error}</div>}
        </div>
      )}
      <button 
        className="btn btn-round" 
        onClick={() => setOpen(!open)}
        aria-label={open ? "Close Demo Panel" : "Open Demo Panel"}
      >
        {open ? <ChevronDown size={20} /> : <ChevronUp size={20} />}
      </button>
    </div>
  );
}

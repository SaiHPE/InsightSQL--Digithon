import { useState } from 'react';
import { Play, RotateCcw, ChevronDown, ChevronUp } from 'lucide-react';

export default function DemoControl({ demo }) {
  const [open, setOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const apiBase = import.meta.env.VITE_API_URL ?? `${window.location.origin}`;

  const start = async () => {
    setLoading(true);
    try { await fetch(`${apiBase}/api/demo/start`, { method: 'POST' }); } catch {}
    setLoading(false);
  };

  const reset = async () => {
    setLoading(true);
    try {
      await fetch(`${apiBase}/api/demo/reset`, { method: 'POST' });
      window.location.reload();
    } catch {}
    setLoading(false);
  };

  const running = demo.phase !== 'idle' && demo.phase !== 'complete';

  return (
    <div className="demo-dock">
      {open && (
        <div className="demo-panel anim-in">
          <div className="demo-btns">
            <button className="btn btn-primary" onClick={start} disabled={loading || running}>
              <Play size={13} /> {running ? 'Running…' : 'Run Demo'}
            </button>
            <button className="btn btn-ghost" onClick={reset} disabled={loading}>
              <RotateCcw size={13} /> Reset
            </button>
          </div>
          {demo.phase !== 'idle' && (
            <>
              <div className="demo-title">
                {demo.phaseNumber > 0 && `${'●'.repeat(demo.phaseNumber)}${'○'.repeat(Math.max(0, 3 - demo.phaseNumber))} `}
                {demo.title}
              </div>
              <div className="demo-talk">"{demo.talkingPoint}"</div>
            </>
          )}
        </div>
      )}
      <button className="btn btn-ghost btn-round" onClick={() => setOpen(!open)}>
        {open ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </button>
    </div>
  );
}

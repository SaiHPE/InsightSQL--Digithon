import { useEffect, useState, useRef } from 'react';
import { Radio, ChevronRight } from 'lucide-react';

/**
 * NarratorBar — HPE-styled demo narrator that sits in the main content area.
 * Shows the current demo phase, title, and talking point with typewriter animation.
 * Only visible when a demo is running (phase !== 'idle').
 *
 * HPE Design Compliance:
 *   - Uses semantic status-info background token
 *   - HPE Graphik typography hierarchy
 *   - Accessible: role="status", aria-live="polite"
 *   - T-Shirt spacing scale
 */
export default function NarratorBar({ demo }) {
  const [displayedText, setDisplayedText] = useState('');
  const textRef = useRef('');
  const intervalRef = useRef(null);

  // Typewriter effect for talking point
  useEffect(() => {
    const fullText = demo.talkingPoint || '';
    if (fullText === textRef.current) return;
    textRef.current = fullText;
    setDisplayedText('');

    if (!fullText) return;

    let i = 0;
    clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      i++;
      setDisplayedText(fullText.slice(0, i));
      if (i >= fullText.length) clearInterval(intervalRef.current);
    }, 18);

    return () => clearInterval(intervalRef.current);
  }, [demo.talkingPoint]);

  if (demo.phase === 'idle') return null;

  const dots = demo.phaseNumber > 0
    ? `${'●'.repeat(demo.phaseNumber)}${'○'.repeat(Math.max(0, 4 - demo.phaseNumber))}`
    : '';

  return (
    <div className="narrator-bar anim-in" role="status" aria-live="polite">
      <div className="narrator-indicator">
        <Radio size={14} className="narrator-pulse" aria-hidden="true" />
        <span className="narrator-label">LIVE DEMO</span>
      </div>

      <div className="narrator-content">
        <div className="narrator-title">
          {dots && <span className="narrator-dots">{dots}</span>}
          <ChevronRight size={14} aria-hidden="true" />
          <span>{demo.title}</span>
        </div>
        <div className="narrator-text">{displayedText}<span className="narrator-cursor">|</span></div>
      </div>

      {demo.phase === 'complete' && (
        <span className="badge badge-ok">Complete</span>
      )}
    </div>
  );
}

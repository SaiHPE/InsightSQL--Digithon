import React from 'react';

export default function Header({ isConnected }) {
  return (
    <div className="header-wrapper">
      {/* HPE Distinctive Brand Asset: Element Bar */}
      <div className="hpe-green-bar" />
      
      <header className="header">
        <div className="header-brand">
          <div className="header-mark">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              {/* Simplified HPE Element representation */}
              <rect x="2" y="6" width="20" height="12" fill="var(--hpe-green)" rx="1" />
            </svg>
          </div>
          <div>
            <div className="header-name">InsightSQL</div>
            <div className="header-sub">HPE GreenLake SAP Operations</div>
          </div>
        </div>

        {/* Global Navigation Pattern */}
        <nav className="header-nav" aria-label="Global Navigation">
          <a href="#" className="header-nav-link active">Dashboard</a>
          <a href="#" className="header-nav-link">Incidents</a>
          <a href="#" className="header-nav-link">Settings</a>
        </nav>

        <div className="header-status" aria-live="polite">
          <div className="status-indicator">
            <div className={`status-dot ${isConnected ? 'active' : 'off'}`} aria-hidden="true" />
            <span>{isConnected ? 'System Live' : 'Reconnecting…'}</span>
          </div>
        </div>
      </header>
    </div>
  );
}

import React, { useState } from 'react';
import { Menu, X } from 'lucide-react';

const NAV_ITEMS = [
  { label: 'Dashboard', id: 'dashboard', active: true },
];

export default function Header({ isConnected }) {
  const [mobileOpen, setMobileOpen] = useState(false);

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

        {/* Desktop Navigation */}
        <nav className="header-nav header-nav-desktop" aria-label="Global Navigation">
          {NAV_ITEMS.map(item => (
            <button
              key={item.id}
              type="button"
              className={`header-nav-link ${item.active ? 'active' : ''}`}
              aria-current={item.active ? 'page' : undefined}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* Mobile menu toggle */}
        <button
          type="button"
          className="btn btn-ghost header-mobile-toggle"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>

        <div className="header-status" aria-live="polite">
          <div className="status-indicator">
            <div className={`status-dot ${isConnected ? 'active' : 'off'}`} aria-hidden="true" />
            <span>{isConnected ? 'System Live' : 'Reconnecting…'}</span>
          </div>
        </div>
      </header>

      {/* Mobile Navigation Dropdown */}
      {mobileOpen && (
        <nav className="header-nav-mobile" aria-label="Mobile Navigation">
          {NAV_ITEMS.map(item => (
            <button
              key={item.id}
              type="button"
              className={`header-nav-link ${item.active ? 'active' : ''}`}
              aria-current={item.active ? 'page' : undefined}
              onClick={() => setMobileOpen(false)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      )}
    </div>
  );
}

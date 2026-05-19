import { useEffect, useState, useRef, useCallback } from 'react';
import useWebSocket from './hooks/useWebSocket';
import useDashboardState from './hooks/useDashboardState';
import Header from './components/Header';
import IncidentBanner from './components/IncidentBanner';
import MetricCards from './components/MetricCards';
import NarratorBar from './components/NarratorBar';
import TimelineChart from './components/TimelineChart';
import TopologyGraph from './components/TopologyGraph';
import EventLog from './components/EventLog';
import DashboardPanels from './components/DashboardPanels';
import AIPanel from './components/AIPanel';

import DemoControl from './components/DemoControl';

export default function App() {
  const { isConnected, lastMessage } = useWebSocket();
  const { state, handleMessage, loadInitialData } = useDashboardState();

  // Track which sections have fresh data for glow effect
  const [glowing, setGlowing] = useState({});
  const glowTimers = useRef({});
  const lastGlowedRef = useRef(null);

  useEffect(() => { loadInitialData(); }, [loadInitialData]);
  useEffect(() => { if (lastMessage) handleMessage(lastMessage); }, [lastMessage, handleMessage]);

  // Stable reference — no deps since it only uses refs and setState
  const triggerGlow = useCallback((sectionId) => {
    lastGlowedRef.current = sectionId;
    setGlowing(prev => ({ ...prev, [sectionId]: true }));
    clearTimeout(glowTimers.current[sectionId]);
    glowTimers.current[sectionId] = setTimeout(() => {
      setGlowing(prev => ({ ...prev, [sectionId]: false }));
    }, 2000);
  }, []);

  // Watch for data changes and trigger section glows
  useEffect(() => {
    if (state.agentSteps.length > 0) triggerGlow('ai');
  }, [state.agentSteps.length, triggerGlow]);

  useEffect(() => {
    if (state.evidence.length > 0) triggerGlow('ai');
  }, [state.evidence.length, triggerGlow]);

  useEffect(() => {
    if (state.rca) triggerGlow('ai');
  }, [state.rca, triggerGlow]);

  useEffect(() => {
    if (state.actions.length > 0) triggerGlow('ai');
  }, [state.actions.length, triggerGlow]);

  useEffect(() => {
    const hasFailed = state.panels.some(p => p.status === 'failed');
    const hasHealed = state.panels.some(p => p.status === 'healed');
    if (hasFailed || hasHealed) triggerGlow('panels');
  }, [state.panels, triggerGlow]);

  // Auto-scroll to the most recently glowed section (not first in object order)
  useEffect(() => {
    const id = lastGlowedRef.current;
    if (id && glowing[id]) {
      document.getElementById(`section-${id}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [glowing]);

  const isInvestigating = state.agentSteps.some(s => s.status === 'running');
  const g = (id) => glowing[id] ? 'section-glow' : '';

  return (
    <div className="app">
      <Header isConnected={isConnected} />

      <main className="main" role="main">
        <div className="main-inner">
          {/* Page Header */}
          <div className="page-header">
            <h1 className="page-title">Operations Dashboard</h1>
            <p className="page-subtitle">HPE GreenLake SAP Operations · InsightSQL</p>
          </div>

          {/* Demo Narrator */}
          <NarratorBar demo={state.demo} />

          {/* Incident Banner */}
          {state.currentIncident && (
            <IncidentBanner incident={state.currentIncident} rca={state.rca} />
          )}

          {/* KPI Cards — 6 cards */}
          <MetricCards latestMetrics={state.latestMetrics} />

          {/* Row 1: Timeline (wide) + Topology (sidebar) */}
          <div className="dash-row-hero">
            <div className="dash-col-wide">
              <TimelineChart metricsTimeline={state.metricsTimeline} />
            </div>
            <div className="dash-col-narrow">
              <TopologyGraph topology={state.topology} />
            </div>
          </div>

          {/* Row 2: Live Dashboard Panels + AI Investigation */}
          <div className="dash-row-panels">
            <div id="section-panels" className={`dash-col-panels ${g('panels')}`}>
              <DashboardPanels
                panels={state.panels}
                panelData={state.panelData}
                healing={state.panelHealing}
              />
            </div>
            <div id="section-ai" className={`dash-col-ai ${g('ai')}`}>
              <AIPanel
                steps={state.agentSteps}
                evidence={state.evidence}
                rca={state.rca}
                actions={state.actions}
              />
            </div>
          </div>

          {/* Row 3: Event Log */}
          <EventLog events={state.eventLog} />
        </div>
      </main>

      <DemoControl demo={state.demo} />
    </div>
  );
}

import { useEffect, useState } from 'react';
import useWebSocket from './hooks/useWebSocket';
import useDashboardState from './hooks/useDashboardState';
import Header from './components/Header';
import IncidentBanner from './components/IncidentBanner';
import MetricCards from './components/MetricCards';
import NarratorBar from './components/NarratorBar';
import TimelineChart from './components/TimelineChart';
import TopologyGraph from './components/TopologyGraph';
import EventLog from './components/EventLog';
import AIReasoningChain from './components/AIReasoningChain';
import EvidencePanel from './components/EvidencePanel';
import PanelHealth from './components/PanelHealth';
import RCANarrative from './components/RCANarrative';
import ActionPanel from './components/ActionPanel';
import ChatInput from './components/ChatInput';
import DemoControl from './components/DemoControl';

const TABS = [
  { id: 'overview',      label: 'Overview' },
  { id: 'investigation', label: 'Investigation' },
  { id: 'panel-health',  label: 'Panel Health' },
];

export default function App() {
  const { isConnected, lastMessage } = useWebSocket();
  const { state, handleMessage, loadInitialData } = useDashboardState();
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => { loadInitialData(); }, [loadInitialData]);
  useEffect(() => { if (lastMessage) handleMessage(lastMessage); }, [lastMessage, handleMessage]);

  useEffect(() => {
    const phase = state.demo.phase;
    // Switch to investigation when agent steps start or evidence arrives
    if (state.agentSteps.length > 0 && activeTab === 'overview') {
      setActiveTab('investigation');
    }
    // Switch to panel-health when panel breaks/heals
    if (phase === 'incident_3' && activeTab !== 'panel-health') {
      setActiveTab('panel-health');
    }
    // Switch to overview for incident 4 (capacity)
    if (phase === 'incident_4' && activeTab === 'panel-health') {
      setActiveTab('investigation');
    }
  }, [state.demo.phase, state.agentSteps.length, activeTab]);

  // Determine if an investigation is actively running (for chat input disabled state)
  const isInvestigating = state.agentSteps.some(s => s.status === 'running');

  return (
    <div className="app">
      <Header isConnected={isConnected} />

      <main className="main" role="main">
        <div className="main-inner">
          {/* Page Header */}
          <div className="page-header">
            <h1 className="page-title">Operations Dashboard</h1>
          </div>

          {/* Demo Narrator — visible during demo */}
          <NarratorBar demo={state.demo} />

          {/* Incident Banner — always visible when active */}
          {state.currentIncident && (
            <IncidentBanner incident={state.currentIncident} rca={state.rca} />
          )}

          {/* KPI Cards — always visible */}
          <MetricCards latestMetrics={state.latestMetrics} />

          {/* Tab Bar */}
          <div className="tab-bar" role="tablist" aria-label="Dashboard sections">
            {TABS.map(tab => (
              <button
                key={tab.id}
                role="tab"
                type="button"
                className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                aria-selected={activeTab === tab.id}
                aria-controls={`tabpanel-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {activeTab === 'overview' && (
            <div id="tabpanel-overview" role="tabpanel" aria-label="Overview" className="tab-panel anim-in">
              <TimelineChart metricsTimeline={state.metricsTimeline} backupWindows={state.backupWindows} />

              <div className="cols-sidebar">
                <TopologyGraph topology={state.topology} />
                <EventLog events={state.eventLog} />
              </div>
            </div>
          )}

          {activeTab === 'investigation' && (
            <div id="tabpanel-investigation" role="tabpanel" aria-label="Investigation" className="tab-panel anim-in">
              <AIReasoningChain steps={state.agentSteps} />
              <EvidencePanel evidence={state.evidence} />

              <div className="cols-2">
                <RCANarrative rca={state.rca} />
                <ActionPanel actions={state.actions} />
              </div>

              <ChatInput
                incidentId={state.currentIncident?.incident_id}
                isInvestigating={isInvestigating}
              />
            </div>
          )}

          {activeTab === 'panel-health' && (
            <div id="tabpanel-panel-health" role="tabpanel" aria-label="Panel Health" className="tab-panel anim-in">
              <PanelHealth panels={state.panels} healing={state.panelHealing} />
            </div>
          )}
        </div>
      </main>

      <DemoControl demo={state.demo} />
    </div>
  );
}

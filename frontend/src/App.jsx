import { useEffect } from 'react';
import useWebSocket from './hooks/useWebSocket';
import useDashboardState from './hooks/useDashboardState';
import Header from './components/Header';
import IncidentBanner from './components/IncidentBanner';
import MetricCards from './components/MetricCards';
import TimelineChart from './components/TimelineChart';
import TopologyGraph from './components/TopologyGraph';
import AIReasoningChain from './components/AIReasoningChain';
import EvidencePanel from './components/EvidencePanel';
import PanelHealth from './components/PanelHealth';
import RCANarrative from './components/RCANarrative';
import DemoControl from './components/DemoControl';

export default function App() {
  const { isConnected, lastMessage } = useWebSocket();
  const { state, handleMessage, loadInitialData } = useDashboardState();

  useEffect(() => { loadInitialData(); }, [loadInitialData]);
  useEffect(() => { if (lastMessage) handleMessage(lastMessage); }, [lastMessage, handleMessage]);

  return (
    <div className="app">
      <Header isConnected={isConnected} />

      <div className="main">
        <div className="main-inner">
          {state.currentIncident && (
            <IncidentBanner incident={state.currentIncident} rca={state.rca} />
          )}

          <MetricCards latestMetrics={state.latestMetrics} />

          <TimelineChart metricsTimeline={state.metricsTimeline} />

          <div className="cols-sidebar">
            <TopologyGraph topology={state.topology} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <AIReasoningChain steps={state.agentSteps} />
              <EvidencePanel evidence={state.evidence} />
            </div>
          </div>

          <div className="cols-2">
            <RCANarrative rca={state.rca} />
            <PanelHealth panels={state.panels} healing={state.panelHealing} />
          </div>
        </div>
      </div>

      <DemoControl demo={state.demo} />
    </div>
  );
}

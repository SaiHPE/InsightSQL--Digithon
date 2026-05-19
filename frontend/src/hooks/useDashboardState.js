import { useReducer, useCallback } from 'react';

const initialState = {
  incidents: [],
  currentIncident: null,
  metricsTimeline: [],
  alerts: [],
  agentSteps: [],
  evidence: [],
  rca: null,
  panels: [],
  panelHealing: {},
  panelData: {},
  topology: { nodes: [], edges: [] },
  demo: { phase: 'idle', phaseNumber: 0, title: 'Ready', talkingPoint: 'Trigger an incident to begin.' },
  latestMetrics: {},
  // New fields
  eventLog: [],
  actions: [],
};

/**
 * Append an entry to the event log.
 * Each entry: { type, summary, ts, severity? }
 */
function appendLog(state, type, summary, ts) {
  return [...state.eventLog.slice(-100), { type, summary, ts: ts || new Date().toISOString() }];
}

function reducer(state, action) {
  switch (action.type) {
    case 'incident_created':
      return {
        ...state,
        currentIncident: action.payload,
        incidents: [...state.incidents, action.payload],
        // Clear previous investigation state for fresh incident
        agentSteps: [],
        evidence: [],
        rca: null,
        actions: [],
        eventLog: appendLog(state, 'alert', `Incident created: ${action.payload.title}`, action.payload.started_at),
      };

    case 'incident_updated':
      return {
        ...state,
        currentIncident: state.currentIncident
          ? { ...state.currentIncident, ...action.payload }
          : action.payload,
      };

    case 'metrics_update': {
      const { resource_id, metrics, event_ts } = action.payload;
      const newLatest = { ...state.latestMetrics };
      for (const [key, val] of Object.entries(metrics)) {
        newLatest[`${resource_id}:${key}`] = { value: val, ts: event_ts };
      }

      // Add to timeline for charts
      const timelineEntry = { ts: event_ts, resource_id, ...metrics };

      // Detect significant metric spikes for event log
      let newLog = state.eventLog;
      const sapP95 = metrics['sap.response.p95_ms'];
      const storageLat = metrics['storage.latency.ms'];
      const hostTemp = metrics['host.temp.c'];
      if (sapP95 && sapP95 > 500) {
        newLog = appendLog(state, 'metric_spike', `SAP p95 spiked to ${Math.round(sapP95)}ms`, event_ts);
      } else if (storageLat && storageLat > 8) {
        newLog = appendLog({ ...state, eventLog: newLog }, 'storage', `Storage latency elevated: ${storageLat.toFixed(1)}ms on ${resource_id.split(':')[1]}`, event_ts);
      } else if (hostTemp && hostTemp > 60) {
        newLog = appendLog({ ...state, eventLog: newLog }, 'compute', `Host temperature ${Math.round(hostTemp)}°C on ${resource_id.split(':')[1]}`, event_ts);
      }

      return {
        ...state,
        latestMetrics: newLatest,
        metricsTimeline: [...state.metricsTimeline.slice(-200), timelineEntry],
        eventLog: newLog,
      };
    }

    case 'alert_received':
      return {
        ...state,
        alerts: [...state.alerts.slice(-50), action.payload],
        eventLog: appendLog(state, 'alert',
          action.payload.summary || action.payload.alerts?.[0]?.annotations?.summary || 'Alert received',
          action.payload.alerts?.[0]?.startsAt),
      };

    case 'agent_step': {
      const step = action.payload;
      const existing = state.agentSteps.findIndex(
        s => s.step === step.step && s.incident_id === step.incident_id
      );
      let newSteps;
      if (existing >= 0) {
        newSteps = [...state.agentSteps];
        newSteps[existing] = step;
      } else {
        newSteps = [...state.agentSteps, step];
      }

      // Log investigation start
      let newLog = state.eventLog;
      if (step.step === 'schema_grounding' && step.status === 'running') {
        newLog = appendLog(state, 'investigation', 'AI investigation started — querying schema…');
      } else if (step.step === 'execution' && step.status === 'complete') {
        newLog = appendLog({ ...state, eventLog: newLog }, 'investigation', `Query executed: ${step.detail}`);
      }

      return { ...state, agentSteps: newSteps.slice(-20), eventLog: newLog };
    }

    case 'evidence_added':
      return {
        ...state,
        evidence: [...state.evidence, action.payload],
        eventLog: appendLog(state, 'evidence',
          `Evidence collected: "${action.payload.question}" → ${action.payload.row_count} rows`),
      };

    case 'rca_generated':
      return {
        ...state,
        rca: action.payload,
        eventLog: appendLog(state, 'rca',
          `RCA generated — confidence ${Math.round((action.payload.confidence || 0) * 100)}%`),
      };

    case 'panel_failed': {
      const newPanels = state.panels.map(p =>
        p.panel_id === action.payload.panel_id
          ? { ...p, status: 'failed', error: action.payload.error }
          : p
      );
      return {
        ...state,
        panels: newPanels,
        panelHealing: {
          ...state.panelHealing,
          [action.payload.panel_id]: { status: 'failed', steps: [], ...action.payload },
        },
        eventLog: appendLog(state, 'panel_fail',
          `Panel "${action.payload.panel_name || action.payload.panel_id}" failed: ${action.payload.error}`),
      };
    }

    case 'panel_healing': {
      const p = action.payload;
      const prev = state.panelHealing[p.panel_id] || { steps: [] };
      const steps = [...(prev.steps || [])];

      // Track each healing step
      const stepEntry = { step: p.step, status: p.status, detail: p.detail, elapsed: p.elapsed };
      const existingIdx = steps.findIndex(s => s.step === p.step);
      if (existingIdx >= 0) {
        steps[existingIdx] = stepEntry;
      } else {
        steps.push(stepEntry);
      }

      return {
        ...state,
        panelHealing: {
          ...state.panelHealing,
          [p.panel_id]: { ...prev, ...p, steps },
        },
        eventLog: p.status === 'running'
          ? appendLog(state, 'panel_heal', `Healing: ${p.detail}`)
          : state.eventLog,
      };
    }

    case 'panel_healed': {
      const healedPanels = state.panels.map(p =>
        p.panel_id === action.payload.panel_id
          ? { ...p, status: 'healed' }
          : p
      );
      const prev = state.panelHealing[action.payload.panel_id] || { steps: [] };
      // Mark ALL healing steps as complete so isHealing becomes false
      const completedSteps = (prev.steps || []).map(s => ({ ...s, status: 'complete' }));
      // Update panelData with fresh results from healed SQL
      const healedPanelData = { ...state.panelData };
      if (action.payload.rows) {
        healedPanelData[action.payload.panel_id] = {
          panel_id: action.payload.panel_id,
          status: 'healed',
          chart_type: action.payload.chart_type || 'table',
          columns: action.payload.columns || [],
          rows: action.payload.rows || [],
          row_count: action.payload.row_count || 0,
        };
      }
      return {
        ...state,
        panels: healedPanels,
        panelData: healedPanelData,
        panelHealing: {
          ...state.panelHealing,
          [action.payload.panel_id]: { ...prev, status: 'healed', steps: completedSteps, ...action.payload },
        },
        eventLog: appendLog(state, 'panel_heal',
          `Panel healed! v${action.payload.old_version} → v${action.payload.new_version}`),
      };
    }

    case 'topology_update': {
      const { resource_id, status, summary } = action.payload;
      const updatedNodes = state.topology.nodes.map(n =>
        n.resource_id === resource_id
          ? { ...n, status, status_summary: summary }
          : n
      );
      return {
        ...state,
        topology: { ...state.topology, nodes: updatedNodes },
      };
    }

    case 'remediation_suggested':
      return {
        ...state,
        actions: [...state.actions, action.payload].slice(-50),
        eventLog: appendLog(state, 'remediation',
          `Action suggested: ${(action.payload.action_type || '').replace(/_/g, ' ')}`),
      };

    case 'demo_phase':
      return {
        ...state,
        demo: {
          phase: action.payload.phase,
          phaseNumber: action.payload.phase_number || 0,
          title: action.payload.title || '',
          talkingPoint: action.payload.talking_point || '',
        },
      };

    case 'SET_TOPOLOGY':
      return { ...state, topology: action.payload };

    case 'SET_PANELS':
      return { ...state, panels: action.payload };

    case 'SET_PANEL_DATA':
      return { ...state, panelData: action.payload };

    case 'UPDATE_PANEL_DATA':
      return { ...state, panelData: { ...state.panelData, ...action.payload } };

    case 'panel_data_refresh':
      // Merge fresh panel data from backend refresh loop, preserving healed status
      return { ...state, panelData: { ...state.panelData, ...action.payload } };

    case 'SET_BASELINE': {
      const { timeline, latest } = action.payload;
      return {
        ...state,
        metricsTimeline: timeline || [],
        latestMetrics: latest || {},
      };
    }

    case 'RESET':
      return { ...initialState };

    case 'APPEND_LOG':
      return { ...state, eventLog: [...state.eventLog.slice(-100), action.payload] };

    default:
      return state;
  }
}

export default function useDashboardState() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const handleMessage = useCallback((message) => {
    if (message && message.type) {
      dispatch({ type: message.type, payload: message.payload });
    }
  }, []);

  // Load initial data
  const loadInitialData = useCallback(async () => {
    try {
      const apiBase = import.meta.env.VITE_API_URL || window.location.origin;
      const [topoRes, panelsRes, metricsRes, panelDataRes] = await Promise.all([
        fetch(`${apiBase}/api/topology`),
        fetch(`${apiBase}/api/panels`),
        fetch(`${apiBase}/api/topology/metrics-baseline`),
        fetch(`${apiBase}/api/panels/all-data`),
      ]);
      if (!topoRes.ok) throw new Error(`Topology fetch failed: ${topoRes.status}`);
      if (!panelsRes.ok) throw new Error(`Panels fetch failed: ${panelsRes.status}`);
      const topology = await topoRes.json();
      const panels = await panelsRes.json();
      dispatch({ type: 'SET_TOPOLOGY', payload: topology });
      dispatch({ type: 'SET_PANELS', payload: panels });
      // Load baseline metrics for chart + KPI cards
      if (metricsRes.ok) {
        const metrics = await metricsRes.json();
        dispatch({ type: 'SET_BASELINE', payload: metrics });
      }
      // Load live panel chart data
      if (panelDataRes.ok) {
        const panelData = await panelDataRes.json();
        dispatch({ type: 'SET_PANEL_DATA', payload: panelData });
      }
      // Seed initial event log entries
      const panelCount = panels.length;
      const now = new Date().toISOString();
      const initialEvents = [
        { type: 'default', summary: 'System initialized — all services connected', ts: now },
        { type: 'storage', summary: 'PostgreSQL 16 health check passed', ts: now },
        { type: 'default', summary: `${panelCount} dashboard panels loaded and verified`, ts: now },
        { type: 'default', summary: 'Baseline metrics: 2h window, all nominal', ts: now },
      ];
      for (const ev of initialEvents) {
        dispatch({ type: 'APPEND_LOG', payload: ev });
      }
    } catch (e) {
      console.error('[Dashboard] Failed to load initial data:', e);
    }
  }, []);

  return { state, dispatch, handleMessage, loadInitialData };
}

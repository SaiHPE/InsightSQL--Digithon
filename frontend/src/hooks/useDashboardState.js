import { useReducer, useEffect, useCallback } from 'react';

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
  topology: { nodes: [], edges: [] },
  demo: { phase: 'idle', phaseNumber: 0, title: 'Ready', talkingPoint: 'Click Run Demo to begin.' },
  latestMetrics: {},
};

function reducer(state, action) {
  switch (action.type) {
    case 'incident_created':
      return {
        ...state,
        currentIncident: action.payload,
        incidents: [...state.incidents, action.payload],
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
      return {
        ...state,
        latestMetrics: newLatest,
        metricsTimeline: [...state.metricsTimeline.slice(-200), timelineEntry],
      };
    }

    case 'alert_received':
      return {
        ...state,
        alerts: [...state.alerts.slice(-50), action.payload],
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
      // Keep last 20 steps
      return { ...state, agentSteps: newSteps.slice(-20) };
    }

    case 'evidence_added':
      return {
        ...state,
        evidence: [...state.evidence, action.payload],
        agentSteps: [], // Clear agent steps after evidence is collected
      };

    case 'rca_generated':
      return {
        ...state,
        rca: action.payload,
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
          [action.payload.panel_id]: { status: 'failed', ...action.payload },
        },
      };
    }

    case 'panel_healing':
      return {
        ...state,
        panelHealing: {
          ...state.panelHealing,
          [action.payload.panel_id]: { ...state.panelHealing[action.payload.panel_id], ...action.payload },
        },
      };

    case 'panel_healed': {
      const healedPanels = state.panels.map(p =>
        p.panel_id === action.payload.panel_id
          ? { ...p, status: 'healed' }
          : p
      );
      return {
        ...state,
        panels: healedPanels,
        panelHealing: {
          ...state.panelHealing,
          [action.payload.panel_id]: { status: 'healed', ...action.payload },
        },
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

    case 'RESET':
      return { ...initialState };

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
      const [topoRes, panelsRes] = await Promise.all([
        fetch('http://localhost:8000/api/topology'),
        fetch('http://localhost:8000/api/panels'),
      ]);
      const topology = await topoRes.json();
      const panels = await panelsRes.json();
      dispatch({ type: 'SET_TOPOLOGY', payload: topology });
      dispatch({ type: 'SET_PANELS', payload: panels });
    } catch (e) {
      console.error('[Dashboard] Failed to load initial data:', e);
    }
  }, []);

  return { state, dispatch, handleMessage, loadInitialData };
}

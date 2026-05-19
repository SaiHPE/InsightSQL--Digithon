import { useState, useEffect, useCallback, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Check, X, Loader2, Wrench, AlertTriangle, RefreshCw, BarChart3, ArrowRight } from 'lucide-react';

/**
 * DashboardPanels — Live mini-chart grid for all seeded dashboard panels.
 * Each panel renders its SQL query results as a sparkline/bar/table/stat.
 * Overlay states: error (red), healing (blue progress), healed (green flash).
 *
 * HPE Design Compliance:
 *   - Card surface pattern with left-border status indicator
 *   - Status colors via semantic tokens
 *   - Accessible: aria-label on status, role="alert" on errors
 */

const CHART_COLORS = {
  panel_sap_p95: '#01A982',
  panel_storage_lat: '#00739D',
  panel_top_hosts: '#7630EA',
  panel_top_volumes: '#FF8300',
  panel_alert_count: '#00C8FF',
};

/** Human-friendly labels for raw column names */
const COLUMN_LABELS = {
  minute: 'Time',
  p95_ms: 'P95 Response (ms)',
  latency_ms: 'Latency (ms)',
  label: 'Name',
  value: 'Value',
  iops: 'IOPS',
  severity: 'Severity',
  count: 'Count',
  resource_name: 'resource_name',
  display_name: 'display_name',
};

/** Short Y-axis unit labels */
const Y_AXIS_LABELS = {
  p95_ms: 'ms',
  latency_ms: 'ms',
  value: '',
  iops: 'IOPS',
  count: '#',
};

/** Descriptive panel subtitle based on panel_id */
const PANEL_DESCRIPTIONS = {
  panel_sap_p95: 'P95 response time over last 30 min',
  panel_storage_lat: 'Avg storage latency over last 30 min',
  panel_top_hosts: 'Avg CPU utilization per host',
  panel_top_volumes: 'Latency & IOPS per volume',
  panel_alert_count: 'Alerts by severity (last hour)',
};

function humanizeCol(col) {
  return COLUMN_LABELS[col] || col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function MiniLineChart({ data, color, xKey, yKey }) {
  const yLabel = Y_AXIS_LABELS[yKey] || humanizeCol(yKey);
  const option = useMemo(() => {
    const chartData = (data || []).map(r => [
      new Date(r[xKey]).getTime(),
      typeof r[yKey] === 'number' ? r[yKey] : parseFloat(r[yKey]) || 0,
    ]);
    return {
      backgroundColor: 'transparent',
      grid: { top: 16, right: 8, bottom: 24, left: 44 },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        axisLabel: { show: true, color: '#5A6872', fontSize: 9, formatter: '{HH}:{mm}' },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        name: yLabel,
        nameTextStyle: { color: '#8899A6', fontSize: 9, padding: [0, 0, 0, 0] },
        nameGap: 6,
        axisLine: { show: false },
        axisLabel: { color: '#8899A6', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(26,31,43,0.95)',
        borderColor: 'rgba(255,255,255,0.1)',
        textStyle: { color: '#C0CADC', fontSize: 11 },
        formatter: params => {
          const p = params[0];
          const ts = new Date(p.value[0]);
          return `<span style="color:#8899A6">${ts.getHours().toString().padStart(2,'0')}:${ts.getMinutes().toString().padStart(2,'0')}</span><br/><b style="color:${color}">${humanizeCol(yKey)}</b>: ${p.value[1]?.toFixed(1)}`;
        },
      },
      series: [{
        type: 'line', data: chartData, smooth: true, symbol: 'none',
        lineStyle: { color, width: 2 },
        areaStyle: {
          color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: color + '30' }, { offset: 1, color: color + '00' }] },
        },
      }],
      animation: true, animationDuration: 300,
    };
  }, [data, color, xKey, yKey, yLabel]);

  return <ReactECharts option={option} style={{ height: 110 }} opts={{ renderer: 'canvas' }} notMerge lazyUpdate />;
}

function MiniBarChart({ data, color, labelKey, valueKey }) {
  const valLabel = humanizeCol(valueKey);
  const option = useMemo(() => {
    const labels = (data || []).map(r => r[labelKey] || '');
    const values = (data || []).map(r => typeof r[valueKey] === 'number' ? r[valueKey] : parseFloat(r[valueKey]) || 0);
    return {
      backgroundColor: 'transparent',
      grid: { top: 8, right: 42, bottom: 4, left: 80 },
      xAxis: { type: 'value', show: false },
      yAxis: {
        type: 'category', data: labels,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: '#C0CADC', fontSize: 11, width: 72, overflow: 'truncate' },
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(26,31,43,0.95)',
        borderColor: 'rgba(255,255,255,0.1)',
        textStyle: { color: '#C0CADC', fontSize: 11 },
        formatter: p => `<b>${labels[p.dataIndex]}</b><br/>${valLabel}: <b style="color:${color}">${p.value?.toFixed?.(1) ?? p.value}</b>`,
      },
      series: [{
        type: 'bar', data: values, barWidth: 14,
        itemStyle: { color, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: '#C0CADC', fontSize: 10,
          formatter: p => p.value?.toFixed?.(1) ?? p.value },
      }],
      animation: true, animationDuration: 300,
    };
  }, [data, color, labelKey, valueKey, valLabel]);

  return <ReactECharts option={option} style={{ height: 100 }} opts={{ renderer: 'canvas' }} notMerge lazyUpdate />;
}

function MiniTable({ data, columns }) {
  if (!data || data.length === 0) return <div className="empty" style={{ fontSize: 11 }}>No data</div>;
  const cols = columns || Object.keys(data[0] || {});
  return (
    <div className="panel-mini-table">
      <table>
        <thead><tr>{cols.map((c, i) => <th key={i}>{humanizeCol(c)}</th>)}</tr></thead>
        <tbody>
          {data.slice(0, 5).map((row, ri) => (
            <tr key={ri}>
              {cols.map((c, ci) => {
                let val = row[c];
                if (val == null) val = '—';
                else if (typeof val === 'number') val = Number.isInteger(val) ? val : val.toFixed(2);
                else val = String(val).slice(0, 20);
                return <td key={ci}>{val}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MiniStat({ data }) {
  if (!data || data.length === 0) return <div className="empty" style={{ fontSize: 11 }}>No alerts</div>;
  return (
    <div className="panel-mini-stats">
      {data.map((row, i) => {
        const sev = row.severity || row.label || `Item ${i + 1}`;
        const count = row.count || row.value || 0;
        const color = sev === 'critical' ? 'var(--status-critical)' : sev === 'warning' ? 'var(--status-warning)' : 'var(--status-info)';
        return (
          <div key={i} className="panel-stat-item">
            <span className="panel-stat-count" style={{ color }}>{count}</span>
            <span className="panel-stat-label">{sev}</span>
          </div>
        );
      })}
    </div>
  );
}

function PanelChart({ panelData }) {
  if (!panelData || panelData.error) return null;
  const { chart_type, rows, columns } = panelData;

  if (chart_type === 'line' && rows?.length > 0) {
    const xKey = columns?.[0] || Object.keys(rows[0])[0];
    const yKey = columns?.[1] || Object.keys(rows[0])[1];
    return <MiniLineChart data={rows} color={CHART_COLORS[panelData.panel_id] || '#01A982'} xKey={xKey} yKey={yKey} />;
  }
  if (chart_type === 'bar' && rows?.length > 0) {
    const labelKey = columns?.[0] || Object.keys(rows[0])[0];
    const valueKey = columns?.[1] || Object.keys(rows[0])[1];
    return <MiniBarChart data={rows} color={CHART_COLORS[panelData.panel_id] || '#7630EA'} labelKey={labelKey} valueKey={valueKey} />;
  }
  if (chart_type === 'table' && rows?.length > 0) {
    return <MiniTable data={rows} columns={columns} />;
  }
  if (chart_type === 'stat') {
    return <MiniStat data={rows} />;
  }
  return <div className="empty" style={{ fontSize: 11 }}>No data</div>;
}

const HEAL_STEP_LABELS = {
  loading: 'Loading Panel',
  diagnosing: 'Diagnosing Error',
  schema_lookup: 'Schema Lookup',
  generating_fix: 'Generating Fix',
  validating_fix: 'Validating Fix',
  promoting: 'Promoting Version',
};

const STATUS_ICON = {
  active: <Check size={12} />,
  failed: <X size={12} />,
  healing: <Loader2 size={12} className="spinner" />,
  healed: <Wrench size={12} />,
};

/**
 * Diff two SQL strings and return tokens with change markers.
 * Highlights the specific words/identifiers that changed.
 */
function diffSqlTokens(oldSql, newSql) {
  if (!oldSql || !newSql) return { oldTokens: [], newTokens: [], changedParts: [] };

  // Tokenize SQL into words, preserving whitespace
  const tokenize = (sql) => sql.split(/(\s+|,|\(|\)|'[^']*')/g).filter(Boolean);
  const oldTokens = tokenize(oldSql);
  const newTokens = tokenize(newSql);

  // Find changed tokens
  const changedParts = [];
  const maxLen = Math.max(oldTokens.length, newTokens.length);
  const oldChanged = new Set();
  const newChanged = new Set();

  for (let i = 0; i < maxLen; i++) {
    if (oldTokens[i] !== newTokens[i]) {
      if (oldTokens[i] && oldTokens[i].trim()) oldChanged.add(i);
      if (newTokens[i] && newTokens[i].trim()) newChanged.add(i);
      if (oldTokens[i]?.trim() && newTokens[i]?.trim()) {
        changedParts.push({ from: oldTokens[i].trim(), to: newTokens[i].trim() });
      }
    }
  }

  return { oldTokens, newTokens, oldChanged, newChanged, changedParts };
}

/** Renders SQL with changed tokens highlighted */
function HighlightedSql({ tokens, changedIndices, type }) {
  const highlightColor = type === 'old' ? 'var(--status-critical)' : 'var(--status-ok)';
  const highlightBg = type === 'old' ? 'rgba(252,97,97,0.15)' : 'rgba(23,235,160,0.15)';
  return (
    <div className={`sql-block ${type}-sql`}>
      {tokens.map((t, i) => {
        if (changedIndices.has(i)) {
          return (
            <span key={i} style={{
              color: highlightColor,
              backgroundColor: highlightBg,
              borderRadius: '3px',
              padding: '1px 3px',
              fontWeight: 600,
              borderBottom: `2px solid ${highlightColor}`,
            }}>{t}</span>
          );
        }
        return <span key={i}>{t}</span>;
      })}
    </div>
  );
}

export default function DashboardPanels({ panels, panelData, healing }) {
  const healingEntries = Object.values(healing || {});

  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">
          <BarChart3 size={16} style={{ marginRight: 'var(--space-3xs)', verticalAlign: 'text-bottom' }} />
          Live Dashboard Panels
        </span>
        <span className="badge badge-info">{panels.length} panels</span>
      </div>
      <div className="section-body" style={{ padding: 'var(--space-sm)' }}>
        <div className="dp-grid">
          {panels.map((p, idx) => {
            const data = panelData?.[p.panel_id];
            const heal = healing?.[p.panel_id];
            const isFailed = p.status === 'failed';
            const isHealed = p.status === 'healed';
            const isHealing = !isHealed && heal?.steps?.some(s => s.status === 'running');
            const description = PANEL_DESCRIPTIONS[p.panel_id];

            return (
              <div key={p.panel_id}
                className={`dp-tile ${isFailed ? 'failed' : ''} ${isHealing ? 'healing' : ''} ${isHealed ? 'healed' : ''} anim-in delay-${idx + 1}`}
              >
                {/* Header */}
                <div className="dp-tile-header">
                  <div style={{ minWidth: 0 }}>
                    <span className="dp-tile-name">{p.panel_name}</span>
                    {description && (
                      <div className="dp-tile-desc">{description}</div>
                    )}
                  </div>
                  <span className={`dp-tile-status ${p.status}`} aria-label={`Status: ${p.status}`}>
                    {STATUS_ICON[p.status] || <Check size={12} />}
                  </span>
                </div>

                {/* Chart area */}
                <div className="dp-tile-chart">
                  {isFailed && !isHealing ? (
                    <div className="dp-error-overlay anim-in" role="alert">
                      <AlertTriangle size={20} />
                      <span className="dp-error-text">{heal?.error || data?.error || 'Query failed'}</span>
                    </div>
                  ) : isHealing ? (
                    <div className="dp-healing-overlay anim-in">
                      <div className="dp-heal-steps">
                        {(heal?.steps || []).map((s, i) => {
                          const cls = s.status === 'complete' ? 'ok' : s.status === 'running' ? 'running' : 'pending';
                          return (
                            <div key={s.step || i} className={`dp-heal-step ${cls}`}>
                              <div className={`dp-heal-dot ${cls}`}>
                                {s.status === 'complete' && <Check size={8} />}
                                {s.status === 'running' && <Loader2 size={8} className="spinner" />}
                              </div>
                              <span>{HEAL_STEP_LABELS[s.step] || s.step}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <PanelChart panelData={data} />
                  )}
                </div>

                {/* Footer stats */}
                <div className="dp-tile-footer">
                  {isHealing ? (
                    <span style={{ color: 'var(--status-info)', fontSize: 11 }}>
                      <RefreshCw size={10} style={{ verticalAlign: 'middle', marginRight: 2 }} className="spinner" />
                      Healing…
                    </span>
                  ) : isFailed ? (
                    <span style={{ color: 'var(--status-critical)', fontSize: 11 }}>SQL Error</span>
                  ) : isHealed ? (
                    <span style={{ color: 'var(--hpe-green)', fontSize: 11 }}>
                      <Wrench size={10} style={{ verticalAlign: 'middle', marginRight: 2 }} /> Auto-healed
                    </span>
                  ) : data?.row_count != null ? (
                    <span style={{ fontSize: 11, color: 'var(--text-xweak)' }}>{data.row_count} rows</span>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>

        {/* SQL diff shown after healing — with column change highlights */}
        {healingEntries.filter(h => h.old_sql && h.new_sql && h.status === 'healed').map(h => {
          const { oldTokens, newTokens, oldChanged, newChanged, changedParts } = diffSqlTokens(h.old_sql, h.new_sql);
          return (
            <div key={h.panel_id} className="dp-sql-diff anim-in">
              {/* Column change callout */}
              {changedParts.length > 0 && (
                <div className="dp-column-change-callout">
                  <Wrench size={14} />
                  <span className="dp-callout-label">Column Fix:</span>
                  {changedParts.slice(0, 3).map((cp, i) => (
                    <span key={i} className="dp-change-pill">
                      <span className="dp-change-from">{cp.from}</span>
                      <ArrowRight size={12} />
                      <span className="dp-change-to">{cp.to}</span>
                    </span>
                  ))}
                </div>
              )}
              <div className="sql-diff">
                <div>
                  <div className="diff-label old"><X size={12} /> Broken SQL</div>
                  <HighlightedSql tokens={oldTokens} changedIndices={oldChanged} type="old" />
                </div>
                <div>
                  <div className="diff-label new"><Check size={12} /> Healed SQL</div>
                  <HighlightedSql tokens={newTokens} changedIndices={newChanged} type="new" />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

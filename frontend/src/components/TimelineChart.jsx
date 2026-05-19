import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

/**
 * TimelineChart — Multi-series telemetry chart with backup window overlay.
 *
 * Series:
 *   1. SAP p95 response time (solid, graph-1 green, left Y)
 *   2. Storage latency (solid, graph-2 teal, right Y)
 *   3. Host temperature (dashed, graph-4 orange, right Y)
 *   4. Host CPU % (dashed, graph-3 purple, right Y)
 *   5. Backup window (markArea overlay)
 *
 * HPE Design Compliance:
 *   - Uses HPE categorical data-visualization palette
 *   - HPE Graphik font in tooltip/legend
 *   - Transparent background (inherits surface)
 *   - Proper contrast text colors for axes
 */
export default function TimelineChart({ metricsTimeline = [], backupWindows = [] }) {
  const option = useMemo(() => {
    const sapData = [];
    const storageData = [];
    const tempData = [];
    const cpuData = [];

    for (const e of metricsTimeline) {
      const ts = new Date(e.ts).getTime();
      if (e['sap.response.p95_ms'] !== undefined) sapData.push([ts, e['sap.response.p95_ms']]);
      if (e['storage.latency.ms'] !== undefined) storageData.push([ts, e['storage.latency.ms']]);
      if (e['host.temp.c'] !== undefined) tempData.push([ts, e['host.temp.c']]);
      if (e['host.cpu.util_pct'] !== undefined) cpuData.push([ts, e['host.cpu.util_pct']]);
    }

    // Backup window markArea data
    const markAreaData = backupWindows.map(bw => ([
      { xAxis: new Date(bw.start).getTime() },
      { xAxis: bw.end ? new Date(bw.end).getTime() : Date.now() },
    ]));

    return {
      backgroundColor: 'transparent',
      grid: { top: 48, right: 64, bottom: 28, left: 56 },
      legend: {
        top: 4, right: 0,
        textStyle: { color: '#8899A6', fontFamily: 'HPE Graphik', fontSize: 12, fontWeight: 500 },
        itemWidth: 14, itemHeight: 3,
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#2d3545',
        borderColor: 'rgba(255,255,255,0.10)',
        textStyle: { color: '#F5F7FA', fontFamily: 'HPE Graphik', fontSize: 12 },
        shadowBlur: 24,
        shadowColor: 'rgba(0,0,0,0.4)',
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        axisLabel: { color: '#8899A6', fontSize: 11 },
        splitLine: { show: false },
      },
      yAxis: [
        {
          type: 'value', name: 'Response (ms)',
          nameTextStyle: { color: '#8899A6', fontSize: 11 },
          axisLine: { show: false },
          axisLabel: { color: '#8899A6', fontSize: 11 },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        },
        {
          type: 'value', name: 'Latency / Temp / CPU',
          nameTextStyle: { color: '#8899A6', fontSize: 11 },
          axisLine: { show: false },
          axisLabel: { color: '#8899A6', fontSize: 11 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: 'SAP p95', type: 'line', yAxisIndex: 0, data: sapData,
          smooth: true, symbol: 'none',
          lineStyle: { color: '#01A982', width: 2 },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: 'rgba(1,169,130,0.18)' }, { offset: 1, color: 'rgba(1,169,130,0)' }],
            },
          },
          markArea: markAreaData.length > 0 ? {
            silent: true,
            itemStyle: { color: 'rgba(255,188,68,0.08)', borderWidth: 1, borderColor: 'rgba(255,188,68,0.3)', borderType: 'dashed' },
            label: {
              show: markAreaData.length > 0,
              position: 'insideTop',
              formatter: 'Backup Running',
              color: '#FFBC44', fontSize: 10, fontWeight: 500, fontFamily: 'HPE Graphik',
            },
            data: markAreaData,
          } : undefined,
        },
        {
          name: 'Storage Latency', type: 'line', yAxisIndex: 1, data: storageData,
          smooth: true, symbol: 'none',
          lineStyle: { color: '#00739D', width: 2 },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: 'rgba(0,115,157,0.15)' }, { offset: 1, color: 'rgba(0,115,157,0)' }],
            },
          },
        },
        ...(tempData.length > 0 ? [{
          name: 'Host Temp (°C)', type: 'line', yAxisIndex: 1, data: tempData,
          smooth: true, symbol: 'none',
          lineStyle: { color: '#FF8300', width: 2, type: 'dashed' },
        }] : []),
        ...(cpuData.length > 0 ? [{
          name: 'Host CPU (%)', type: 'line', yAxisIndex: 1, data: cpuData,
          smooth: true, symbol: 'none',
          lineStyle: { color: '#7630EA', width: 2, type: 'dashed' },
        }] : []),
      ],
      animation: true, animationDuration: 400,
    };
  }, [metricsTimeline, backupWindows]);

  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">Telemetry Timeline</span>
        <span style={{ fontSize: 12, color: 'var(--text-weak)' }}>
          SAP Response · Storage Latency · Host Metrics · Backup Window
        </span>
      </div>
      <div className="section-body" style={{ padding: 'var(--space-xs) var(--space-md)' }}>
        {metricsTimeline.length > 0 ? (
          <ReactECharts option={option} style={{ height: 240 }} opts={{ renderer: 'canvas' }} notMerge={false} lazyUpdate />
        ) : (
          <div className="empty" style={{ height: 240 }}>Waiting for telemetry…</div>
        )}
      </div>
    </div>
  );
}

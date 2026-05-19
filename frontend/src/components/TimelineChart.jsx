import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

export default function TimelineChart({ metricsTimeline = [] }) {
  const option = useMemo(() => {
    const sapData = [];
    const storageData = [];

    for (const e of metricsTimeline) {
      const ts = new Date(e.ts).getTime();
      if (e['sap.response.p95_ms'] !== undefined) sapData.push([ts, e['sap.response.p95_ms']]);
      if (e['storage.latency.ms'] !== undefined) storageData.push([ts, e['storage.latency.ms']]);
    }

    return {
      backgroundColor: 'transparent',
      grid: { top: 40, right: 56, bottom: 28, left: 56 },
      legend: {
        top: 4, right: 0,
        textStyle: { color: 'var(--text-weak)', fontFamily: 'HPE Graphik', fontSize: 12, fontWeight: 500 },
        itemWidth: 14, itemHeight: 3,
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'var(--bg-floating)',
        borderColor: 'var(--border-default)',
        textStyle: { color: 'var(--text-strong)', fontFamily: 'HPE Graphik', fontSize: 12 },
        shadowBlur: 24,
        shadowColor: 'rgba(0,0,0,0.4)'
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: 'var(--border-weak)' } },
        axisLabel: { color: 'var(--text-weak)', fontSize: 11 },
        splitLine: { show: false },
      },
      yAxis: [
        {
          type: 'value', name: 'Response (ms)',
          nameTextStyle: { color: 'var(--text-weak)', fontSize: 11 },
          axisLine: { show: false },
          axisLabel: { color: 'var(--text-weak)', fontSize: 11 },
          splitLine: { lineStyle: { color: 'var(--border-weak)' } },
        },
        {
          type: 'value', name: 'Latency (ms)',
          nameTextStyle: { color: 'var(--text-weak)', fontSize: 11 },
          axisLine: { show: false },
          axisLabel: { color: 'var(--text-weak)', fontSize: 11 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: 'SAP p95', type: 'line', yAxisIndex: 0, data: sapData,
          smooth: true, symbol: 'none',
          lineStyle: { color: 'var(--graph-1)', width: 2 },
          areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(1,169,130,0.15)' }, { offset: 1, color: 'rgba(1,169,130,0)' }] } },
        },
        {
          name: 'Storage Latency', type: 'line', yAxisIndex: 1, data: storageData,
          smooth: true, symbol: 'none',
          lineStyle: { color: 'var(--graph-2)', width: 2 },
          areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(0,115,157,0.15)' }, { offset: 1, color: 'rgba(0,115,157,0)' }] } },
        },
      ],
      animation: true, animationDuration: 400,
    };
  }, [metricsTimeline]);

  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">Telemetry Timeline</span>
        <span style={{ fontSize: 12, color: 'var(--text-weak)' }}>SAP Response vs Storage Latency</span>
      </div>
      <div className="section-body" style={{ padding: 'var(--space-xs) var(--space-md)' }}>
        {metricsTimeline.length > 0 ? (
          <ReactECharts option={option} style={{ height: 220 }} opts={{ renderer: 'canvas' }} notMerge={false} lazyUpdate />
        ) : (
          <div className="empty" style={{ height: 220 }}>Waiting for telemetry…</div>
        )}
      </div>
    </div>
  );
}

import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

export default function TimelineChart({ metricsTimeline }) {
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
        textStyle: { color: '#7d8a92', fontFamily: 'HPE Graphik', fontSize: 11 },
        itemWidth: 14, itemHeight: 2,
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#222528',
        borderColor: 'rgba(255,255,255,0.1)',
        textStyle: { color: '#f0f1f2', fontFamily: 'HPE Graphik', fontSize: 11 },
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        axisLabel: { color: '#7d8a92', fontSize: 10 },
        splitLine: { show: false },
      },
      yAxis: [
        {
          type: 'value', name: 'Response (ms)',
          nameTextStyle: { color: '#7d8a92', fontSize: 10 },
          axisLine: { show: false },
          axisLabel: { color: '#7d8a92', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } },
        },
        {
          type: 'value', name: 'Latency (ms)',
          nameTextStyle: { color: '#7d8a92', fontSize: 10 },
          axisLine: { show: false },
          axisLabel: { color: '#7d8a92', fontSize: 10 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: 'SAP p95', type: 'line', yAxisIndex: 0, data: sapData,
          smooth: true, symbol: 'none',
          lineStyle: { color: '#01A982', width: 2 },
          areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(1,169,130,0.12)' }, { offset: 1, color: 'rgba(1,169,130,0)' }] } },
        },
        {
          name: 'Storage Latency', type: 'line', yAxisIndex: 1, data: storageData,
          smooth: true, symbol: 'none',
          lineStyle: { color: '#62E5F6', width: 2 },
          areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(98,229,246,0.08)' }, { offset: 1, color: 'rgba(98,229,246,0)' }] } },
        },
      ],
      animation: true, animationDuration: 300,
    };
  }, [metricsTimeline]);

  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">Telemetry Timeline</span>
        <span style={{ fontSize: 11, color: 'var(--t3)' }}>SAP Response vs Storage Latency</span>
      </div>
      <div className="section-body" style={{ padding: '8px 12px' }}>
        {metricsTimeline.length > 0 ? (
          <ReactECharts option={option} style={{ height: 220 }} opts={{ renderer: 'canvas' }} notMerge={false} lazyUpdate />
        ) : (
          <div className="empty" style={{ height: 220 }}>Waiting for telemetry…</div>
        )}
      </div>
    </div>
  );
}

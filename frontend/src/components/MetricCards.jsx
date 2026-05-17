const CARDS = [
  { key: 'sap_sid:PRD:sap.response.p95_ms', label: 'SAP P95 Response', unit: 'ms', baseline: 145, warn: 300, crit: 500 },
  { key: 'array:primera-prod-01:storage.latency.ms', label: 'Storage Latency', unit: 'ms', baseline: 2.1, warn: 5, crit: 8 },
  { key: 'host:prd-hana-02:host.temp.c', label: 'Host Temperature', unit: '°C', baseline: 40, warn: 55, crit: 65 },
  { key: 'host:prd-hana-02:host.cpu.util_pct', label: 'Host CPU', unit: '%', baseline: 45, warn: 70, crit: 85 },
];

export default function MetricCards({ latestMetrics }) {
  return (
    <div className="kpi-row">
      {CARDS.map(c => {
        const d = latestMetrics[c.key];
        const val = d ? Math.round(d.value * 10) / 10 : c.baseline;
        const status = val >= c.crit ? 'crit' : val >= c.warn ? 'warn' : '';
        const delta = c.baseline > 0 ? Math.round(((val - c.baseline) / c.baseline) * 100) : 0;
        const isUp = delta > 10;

        return (
          <div key={c.key} className={`kpi ${status}`}>
            <div className="kpi-label">{c.label}</div>
            <div className="kpi-value">
              {val.toLocaleString()}
              <span className="kpi-unit">{c.unit}</span>
            </div>
            <div className={`kpi-delta ${isUp ? 'up' : ''}`}>
              {isUp ? `▲ ${delta}% from baseline` : `baseline: ${c.baseline}${c.unit}`}
            </div>
          </div>
        );
      })}
    </div>
  );
}

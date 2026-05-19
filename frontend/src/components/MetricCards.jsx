import { Activity, HardDrive, Thermometer, Cpu, ArrowUp, ArrowDown } from 'lucide-react';

const CARDS = [
  { key: 'sap_sid:PRD:sap.response.p95_ms', label: 'SAP P95 Response', unit: 'ms', baseline: 145, warn: 300, crit: 500, icon: Activity },
  { key: 'array:primera-prod-01:storage.latency.ms', label: 'Storage Latency', unit: 'ms', baseline: 2.1, warn: 5, crit: 8, icon: HardDrive },
  { key: 'host:prd-hana-02:host.temp.c', label: 'Host Temperature', unit: '°C', baseline: 40, warn: 55, crit: 65, icon: Thermometer },
  { key: 'host:prd-hana-02:host.cpu.util_pct', label: 'Host CPU', unit: '%', baseline: 45, warn: 70, crit: 85, icon: Cpu },
];

export default function MetricCards({ latestMetrics }) {
  return (
    <div className="kpi-row">
      {CARDS.map((c, idx) => {
        const d = latestMetrics[c.key];
        const val = d ? Math.round(d.value * 10) / 10 : c.baseline;
        const status = val >= c.crit ? 'crit' : val >= c.warn ? 'warn' : '';
        const delta = c.baseline > 0 ? Math.round(((val - c.baseline) / c.baseline) * 100) : 0;
        const isUp = delta > 10;
        const isDown = delta < -10;
        const Icon = c.icon;

        return (
          <div key={c.key} className={`kpi ${status} anim-in delay-${idx + 1}`}>
            <div className="kpi-header">
              <span className="kpi-label">{c.label}</span>
              <Icon size={16} className="kpi-icon" aria-hidden="true" />
            </div>
            <div className="kpi-value">
              {val.toLocaleString()}
              <span className="kpi-unit">{c.unit}</span>
            </div>
            <div className={`kpi-delta ${isUp ? 'up' : isDown ? 'down' : ''}`}>
              {isUp && <ArrowUp size={12} />}
              {isDown && <ArrowDown size={12} />}
              <span>{isUp || isDown ? `${Math.abs(delta)}% from baseline` : `Baseline: ${c.baseline}${c.unit}`}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

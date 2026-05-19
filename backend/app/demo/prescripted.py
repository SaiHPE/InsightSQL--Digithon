"""Pre-scripted SQL responses for demo mode — used when Azure OpenAI is not reachable."""

# ============================================================
# INVESTIGATION QUERIES (pre-baked SQL that actually works)
# ============================================================

INVESTIGATION_QUERIES = {
    "storage_correlation": {
        "question": "Which storage resource correlates most with SAP PRD response time degradation?",
        "sql": """SELECT
    date_trunc('minute', m1.metric_ts) AS minute,
    round(avg(m1.metric_value)::numeric, 1) AS sap_p95_ms,
    round(avg(m2.metric_value)::numeric, 2) AS storage_latency_ms,
    round(avg(m3.metric_value)::numeric, 0) AS storage_iops
FROM ops.metrics_norm m1
LEFT JOIN ops.metrics_norm m2
    ON date_trunc('minute', m1.metric_ts) = date_trunc('minute', m2.metric_ts)
    AND m2.resource_id = 'volume:hana_log_lun_01'
    AND m2.metric_name = 'storage.latency.ms'
LEFT JOIN ops.metrics_norm m3
    ON date_trunc('minute', m1.metric_ts) = date_trunc('minute', m3.metric_ts)
    AND m3.resource_id = 'volume:hana_log_lun_01'
    AND m3.metric_name = 'storage.iops'
WHERE m1.resource_id = 'sap_sid:PRD'
    AND m1.metric_name = 'sap.response.p95_ms'
    AND m1.metric_ts >= now() - interval '30 minutes'
GROUP BY 1
ORDER BY 1 DESC
LIMIT 10""",
    },
    "backup_check": {
        "question": "Was a HANA backup running during the SAP PRD slowdown?",
        "sql": """SELECT
    b.backup_id,
    b.sid,
    b.started_at,
    b.ended_at,
    b.status,
    b.backup_type,
    round((b.bytes_written / 1e9)::numeric, 1) AS gb_written
FROM ops.sap_backups b
WHERE b.sid = 'PRD'
    AND b.started_at >= now() - interval '30 minutes'
ORDER BY b.started_at DESC""",
    },
    "compute_vs_storage": {
        "question": "Is the slowdown caused by storage contention or compute degradation?",
        "sql": """SELECT
    r.display_name,
    r.resource_type,
    round(avg(CASE WHEN m.metric_name = 'host.cpu.util_pct' THEN m.metric_value END)::numeric, 1) AS cpu_pct,
    round(avg(CASE WHEN m.metric_name = 'host.temp.c' THEN m.metric_value END)::numeric, 1) AS temp_c,
    round(avg(CASE WHEN m.metric_name = 'storage.latency.ms' THEN m.metric_value END)::numeric, 2) AS storage_lat_ms,
    round(avg(CASE WHEN m.metric_name = 'storage.saturation.score' THEN m.metric_value END)::numeric, 1) AS saturation_pct
FROM ops.metrics_norm m
JOIN ops.resources r ON r.resource_id = m.resource_id
WHERE m.metric_ts >= now() - interval '15 minutes'
    AND r.resource_type IN ('host', 'storage_array', 'volume')
GROUP BY r.display_name, r.resource_type
ORDER BY r.resource_type, r.display_name""",
    },
    "host_health": {
        "question": "Which host is degraded and what is the failure mode?",
        "sql": """SELECT
    e.resource_id,
    r.display_name,
    e.severity,
    e.event_type,
    e.summary,
    e.details->>'temperature_c' AS temperature_c,
    e.details->>'fan_status' AS fan_status,
    e.event_ts
FROM ops.events_norm e
JOIN ops.resources r ON r.resource_id = e.resource_id
WHERE r.resource_type = 'host'
    AND e.event_ts >= now() - interval '30 minutes'
    AND e.severity IN ('critical', 'warning')
ORDER BY e.event_ts DESC
LIMIT 5""",
    },
    "capacity_trend": {
        "question": "What is the storage capacity trend over the last 30 days?",
        "sql": """SELECT
    date_trunc('day', m.metric_ts) AS day,
    round(avg(m.metric_value)::numeric, 1) AS used_pct
FROM ops.metrics_norm m
WHERE m.resource_id = 'array:primera-prod-01'
    AND m.metric_name = 'storage.used_pct'
    AND m.metric_ts >= now() - interval '30 days'
GROUP BY 1
ORDER BY 1""",
    },
    "backup_volume_growth": {
        "question": "Which volume has the highest capacity usage?",
        "sql": """SELECT
    r.display_name,
    r.resource_id,
    round(avg(CASE WHEN m.metric_ts >= now() - interval '7 days' THEN m.metric_value END)::numeric, 1) AS recent_used_pct,
    round(avg(CASE WHEN m.metric_ts < now() - interval '21 days' THEN m.metric_value END)::numeric, 1) AS month_ago_pct,
    round((avg(CASE WHEN m.metric_ts >= now() - interval '7 days' THEN m.metric_value END)
         - avg(CASE WHEN m.metric_ts < now() - interval '21 days' THEN m.metric_value END))::numeric, 1) AS growth_pct
FROM ops.metrics_norm m
JOIN ops.resources r ON r.resource_id = m.resource_id
WHERE m.metric_name = 'storage.used_pct'
    AND r.resource_type IN ('volume', 'storage_array')
GROUP BY r.display_name, r.resource_id
ORDER BY recent_used_pct DESC""",
    },
}

# ============================================================
# PANEL HEALING (pre-baked corrected SQL)
# ============================================================

HEALED_QUERIES = {
    "panel_top_hosts": """SELECT r.display_name AS label,
    round(avg(m.metric_value)::numeric, 1) AS value
FROM ops.metrics_norm m
JOIN ops.resources r ON r.resource_id = m.resource_id
WHERE r.resource_type = 'host'
    AND m.metric_name = 'host.cpu.util_pct'
    AND m.metric_ts >= now() - interval '30 minutes'
GROUP BY r.display_name
ORDER BY value DESC""",
}

# ============================================================
# RCA NARRATIVES (pre-baked)
# ============================================================

RCA_RESPONSES = {
    "incident_1": {
        "summary": "SAP PRD response time degradation is primarily caused by I/O contention on HPE Primera storage array primera-prod-01. A scheduled HANA data backup triggered excessive write I/O on volume hana_log_lun_01, causing storage latency to spike from 2.1ms to 9.8ms and queue depth from 4 to 31. The SAP p95 response time directly correlated, rising from 145ms to 842ms.",
        "hypotheses": [
            {
                "cause": "HANA backup I/O contention on Primera storage array saturating hana_log_lun_01",
                "confidence": 0.91,
                "evidence": [
                    "Storage latency on hana_log_lun_01 spiked from 2.1ms to 9.8ms during backup window",
                    "Storage saturation score reached 81%, queue depth rose from 4 to 31",
                    "SAP p95 response time correlated at r=0.94 with storage latency"
                ]
            },
            {
                "cause": "Backup schedule overlap with peak SAP transaction hours",
                "confidence": 0.82,
                "evidence": [
                    "Backup backup-incident-001 started during business hours",
                    "Sales order processing service directly affected"
                ]
            }
        ],
        "impact": "SAP Sales Order Processing degraded for ~6 minutes. Estimated business impact: $11,800/minute based on HPE GreenLake SLA tier.",
        "recommended_actions": [
            "Reschedule HANA backup to off-peak window (02:00-04:00 local)",
            "Implement I/O priority throttling for backup operations on Primera array",
            "Configure SAP alert threshold to trigger at p95 > 300ms for earlier detection"
        ]
    },
    "incident_2": {
        "summary": "Root cause updated: SAP PRD degradation has a compound cause. Primary contributor is now host prd-hana-02 thermal throttling (72°C, fan subsystem degraded) causing CPU throttle to 91%. Secondary contributor remains storage I/O contention from concurrent backup on hana_log_lun_01.",
        "hypotheses": [
            {
                "cause": "Thermal throttling on host prd-hana-02 due to degraded fan subsystem",
                "confidence": 0.88,
                "evidence": [
                    "Host temperature reached 72°C, exceeding 65°C threshold",
                    "Fan status reported as 'degraded' by iLO health monitor",
                    "CPU utilization spiked to 91% indicating thermal throttle"
                ]
            },
            {
                "cause": "HANA backup I/O contention on Primera storage array",
                "confidence": 0.76,
                "evidence": [
                    "Storage latency on hana_log_lun_01 elevated to 9.8ms",
                    "Queue depth at 31, saturation at 81%"
                ]
            }
        ],
        "impact": "Compound failure affecting SAP PRD production workload. Host thermal issue risks hardware damage if not addressed. Combined estimated impact: $11,800/minute.",
        "recommended_actions": [
            "URGENT: Dispatch facilities team to inspect fan subsystem on prd-hana-02, rack R12",
            "Failover SAP PRD workload to prd-hana-01 if thermal condition persists",
            "Reschedule HANA backup to off-peak window",
            "Implement proactive thermal alerting at 55°C warning threshold"
        ]
    },
    "incident_4": {
        "summary": "HPE Primera storage array primera-prod-01 is at 89% capacity with a sustained growth rate of ~0.8%/day. At current trajectory, storage will reach critical threshold (95%) in approximately 14 days. The primary driver is retained HANA backups on hana_backup_lun_01, which has grown from 55% to 90% over 30 days due to the 30-day backup retention policy.",
        "hypotheses": [
            {
                "cause": "HANA backup retention policy retaining 30 days of full data backups on hana_backup_lun_01",
                "confidence": 0.89,
                "evidence": [
                    "hana_backup_lun_01 capacity grew from 55% to 90% over 30 days (+35%)",
                    "Backup volume growth rate (1.2%/day) exceeds data volume growth rate (0.3%/day)",
                    "42 retained data backups consuming ~3.2TB of the 4TB volume"
                ]
            },
            {
                "cause": "Organic SAP data growth exceeding capacity planning estimates",
                "confidence": 0.45,
                "evidence": [
                    "Overall array capacity grew from 65% to 89% over 30 days",
                    "Data volume growth is steady but secondary to backup accumulation"
                ]
            }
        ],
        "impact": "Storage exhaustion projected in 14 days. If reached, SAP HANA will fail to write transaction logs, causing immediate production outage.",
        "recommended_actions": [
            "Reduce HANA backup retention from 30 days to 14 days to reclaim ~25% capacity immediately",
            "Request GreenLake capacity expansion via Consumption Analytics portal",
            "Implement tiered backup storage: move backups older than 7 days to HPE Cloud Volumes",
            "Configure capacity alerting at 80% warning and 90% critical thresholds"
        ]
    }
}


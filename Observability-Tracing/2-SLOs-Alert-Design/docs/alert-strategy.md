# Multi-Window, Multi-Burn-Rate Alert Strategy

This strategy provides reliable alerting for both fast-moving incidents and slow-burning issues by using three time windows: 5 minutes, 30 minutes, and 6 hours.

## Benefits:
- Reduces false positives by requiring issues to persist
- Detects both sudden spikes and slow degradation
- Conserves error budget by alerting before full exhaustion

## Windows Used:
- **Fast burn**: 5m & 30m window – detects spikes quickly
- **Slow burn**: 30m & 6h window – detects gradual issues

## Burn Rate Thresholds:
- Latency: 0.86 (14.4x fast burn), 0.94 (6x slow burn)
- Error: 0.986 (fast), 0.994 (slow)
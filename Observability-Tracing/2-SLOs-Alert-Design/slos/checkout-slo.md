# Service Level Objectives for Checkout API

## Latency SLO
- **Target**: 99% of requests complete in under 500ms
- **Time Window**: 30-day rolling window
- **Error Budget**: 1% (432 minutes of slow responses per 30 days)

## Error Rate SLO
- **Target**: 99.9% of requests return non-5xx responses
- **Time Window**: 30-day rolling window
- **Error Budget**: 0.1% (43.2 minutes of errors per 30 days)

# Runbook for Checkout API Alerts

## Alert: CheckoutLatencySLOFastBurn
- **Impact**: >14.4x burn rate, critical latency issues
- **Actions**:
  - Check upstream service latency (e.g., payment, inventory)
  - Review recent deployments or scaling changes
  - Inspect node or pod CPU/memory pressure

## Alert: CheckoutErrorSLOFastBurn
- **Impact**: >144x burn rate, high error rate
- **Actions**:
  - Check application logs for stack traces
  - Verify dependencies (e.g., database, cache availability)
  - Roll back recent code changes if applicable

## Alert: Slow Burn Alerts
- Monitor over time; escalate if persists beyond typical baselines
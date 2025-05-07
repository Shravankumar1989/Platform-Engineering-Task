# Checkout API SLO and Alerting Configuration

This repository defines Service Level Indicators (SLIs), Service Level Objectives (SLOs), Prometheus recording rules, and alerting rules for the `/checkout` endpoint of the `checkout-api` service.

## Structure

- `slis/`: PromQL queries defining SLIs
- `slos/`: Markdown documentation of latency and error rate SLOs
- `rules/`: Prometheus recording and alerting rules
- `docs/`: Alerting strategy explanations
- `runbooks/`: Operational guidance for handling alerts
# Monitoring Setup Guide

Track these runtime signals from `logs/*.log`:

- requests per hour/day
- total errors
- CAPTCHA encounters
- unique affiliators scraped
- run duration and checkpoint frequency

Recommended alert thresholds:

- `errors >= max_errors_before_stop`
- `captchas >= max_captchas_before_stop`
- no new records for 20+ minutes

If needed, ship logs to your existing stack (ELK, Loki, Datadog).

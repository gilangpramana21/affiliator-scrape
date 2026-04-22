# Proxy Configuration Guide

Use proxies only if operationally required and contractually allowed.

`config` fields:

- `proxies`: list of proxy entries `{protocol, host, port, username, password}`
- `proxy_rotation_strategy`: `per_session`, `per_request`, `round_robin`, etc.
- `proxy_rotation_interval`: used by `per_n_requests`

Best practices:

- start with one stable proxy before enabling rotation
- monitor failure rate and disable unhealthy proxies
- avoid aggressive rotation + high request rates simultaneously

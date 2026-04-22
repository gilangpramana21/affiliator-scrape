# Distributed Deployment

1. Prepare dependencies:
   - `bash scripts/setup_distributed.sh`
2. Edit `config/config.distributed.json`:
   - set `"distributed": true`
   - set `"redis_url": "redis://localhost:6379/0"`
   - set a unique `"instance_id"` per node
3. Run each node:
   - `./venv/bin/python main.py --config config/config.distributed.json`
4. Monitor `logs/` and Redis health.

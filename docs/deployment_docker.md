# Docker Deployment

1. Build and run:
   - `docker compose up --build`
2. Ensure `config/cookies.json` exists before startup.
3. Output files are persisted in host `output/`.
4. Logs are persisted in host `logs/`.

For scraper only (without Redis):
- `docker build -t affiliator-scraper .`
- `docker run --rm -v $(pwd)/config:/app/config -v $(pwd)/output:/app/output -v $(pwd)/logs:/app/logs affiliator-scraper`

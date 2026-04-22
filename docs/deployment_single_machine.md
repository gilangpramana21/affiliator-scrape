# Single Machine Deployment

1. Run setup:
   - `bash scripts/setup_single_machine.sh`
2. Convert/export cookies:
   - `make convert-cookies IN=cookies-export.json OUT=config/cookies.json`
3. Validate runtime readiness:
   - `make preflight`
4. Start scraper:
   - `make run-safe`
5. Resume if interrupted:
   - `make run-safe-resume`

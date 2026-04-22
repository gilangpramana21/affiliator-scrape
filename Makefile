PYTHON := ./venv/bin/python
SAFE_CONFIG := config/config.safe.json
SAFE_CHECKPOINT := output/affiliators.safe_checkpoint.json

.PHONY: help preflight convert-cookies perf-profile load-test run-safe run-safe-resume validate-safe-config

help:
	@echo "Targets:"
	@echo "  make preflight           Check config + cookie readiness"
	@echo "  make convert-cookies IN=path/to/export.json [OUT=config/cookies.json]"
	@echo "  make perf-profile        Run parser/datastore performance profile"
	@echo "  make load-test           Run stability harness (default 10 minutes)"
	@echo "  make run-safe            Run scraper with safe config"
	@echo "  make run-safe-resume     Resume from safe checkpoint"
	@echo "  make validate-safe-config Validate safe config file"

preflight:
	@$(PYTHON) tools/preflight.py --config "$(SAFE_CONFIG)"

convert-cookies:
	@$(PYTHON) tools/convert_cookies.py --input "$(IN)" --output "$(if $(OUT),$(OUT),config/cookies.json)"

perf-profile:
	@$(PYTHON) tools/performance_profile.py

load-test:
	@$(PYTHON) tools/load_test_harness.py --minutes "$(if $(MINUTES),$(MINUTES),10)" --batch-size "$(if $(BATCH_SIZE),$(BATCH_SIZE),200)"

validate-safe-config:
	@$(PYTHON) -c "from src.models.config import Configuration as C; c=C.from_file('$(SAFE_CONFIG)'); e=c.validate(); print('OK' if not e else '\n'.join(e)); raise SystemExit(0 if not e else 1)"

run-safe:
	@$(PYTHON) main.py --config "$(SAFE_CONFIG)"

run-safe-resume:
	@$(PYTHON) main.py --config "$(SAFE_CONFIG)" --resume-checkpoint "$(SAFE_CHECKPOINT)"

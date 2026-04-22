# Manual Verification Checklist

Use this checklist for tasks requiring external/manual validation.

## Anti-Detection Verification (Task 27)

- [ ] Run browser fingerprint test manually on CreepJS
- [ ] Run bot detection page manually on bot.sannysoft.com
- [ ] Run TLS fingerprint check manually on BrowserLeaks
- [ ] Record behavior replay evidence (mouse/scroll/idle)
- [ ] Run a scoped real-world test on affiliate center
- [ ] Record success/block/CAPTCHA rate and adjust config

## Production Testing (Task 32)

- [ ] Dry run on target environment with safe config
- [ ] Monitor errors and CAPTCHA trend during run
- [ ] Measure success rate
- [ ] Measure scraping speed (records/minute)
- [ ] Apply config tuning and rerun
- [ ] Final sign-off after stable repeated runs

## Notes Template

- Run date:
- Config used:
- Duration:
- Total scraped:
- Errors:
- CAPTCHA count:
- Blocked sessions:
- Actions taken:

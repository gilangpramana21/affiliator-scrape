# Troubleshooting Guide

## Preflight fails
- Ensure `config/cookies.json` exists.
- Re-export and reconvert cookies, then rerun `make preflight`.

## No data extracted
- Recheck selectors in `config/selectors.json`.
- Confirm account can open creator list and detail pages manually.

## Too many CAPTCHAs
- Pause runs, lower traffic limits, shorten run scope (`max_pages_per_run`).
- Resume with checkpoint once stable.

## Output file missing
- Verify `output_format` and `output_path` in config.
- Check write permissions for `output/`.

# Manual Tests

This directory contains manual testing scripts that require human inspection or interaction.

## Available Tests

### 1. CreepJS Fingerprint Detection Test

**Purpose**: Verify that browser fingerprint randomization is working correctly and cannot be detected by advanced fingerprinting tools.

**Script**: `test_creepjs_fingerprint.py`

**Documentation**: See `docs/manual_tests/creepjs_guide.md` for detailed instructions

**Quick Start**:
```bash
# Run with visible browser (recommended)
python tests/manual/test_creepjs_fingerprint.py

# Run in headless mode
python tests/manual/test_creepjs_fingerprint.py --headless
```

**Success Criteria**:
- Trust score ≥ 70%
- Lies detected ≤ 2
- No critical bot indicators

## Why Manual Tests?

Manual tests are necessary when:
1. **Visual inspection is required** - Some aspects of anti-detection can only be verified by human observation
2. **Third-party tools are involved** - Testing against external services like CreepJS
3. **Subjective evaluation needed** - Determining if behavior "looks human" requires human judgment
4. **Interactive debugging** - Stepping through browser behavior in real-time

## Running All Manual Tests

```bash
# Run all manual tests in sequence
for test in tests/manual/test_*.py; do
    echo "Running $test..."
    python "$test"
    echo "---"
done
```

## Adding New Manual Tests

When adding a new manual test:

1. **Create the test script** in this directory with prefix `test_`
2. **Add documentation** in `docs/manual_tests/` explaining:
   - What the test does
   - How to run it
   - How to interpret results
   - Success/failure criteria
3. **Update this README** with a summary of the new test
4. **Make it executable**: `chmod +x tests/manual/test_*.py`

## Best Practices

- ✅ Always document expected results
- ✅ Provide clear pass/fail criteria
- ✅ Include troubleshooting steps
- ✅ Make tests repeatable
- ✅ Support both headed and headless modes when possible
- ✅ Add screenshots or examples of expected output

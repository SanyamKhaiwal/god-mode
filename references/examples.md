# Worked examples

## Triage decisions

**"Rename `maxRpm` to `rpmLimit` everywhere."**
Route: Direct. Exact spec, mechanical, existing tests cover it.

**"Add a setting to toggle units between metric and imperial on the telemetry panel."**
Route: Light. About 4 files (settings model, settings UI, telemetry widget, formatter), clear goal, formatter tests exist.

**"Tire grip feels wrong at high slip angles, make drifting more realistic."**
Route: Full. Vague spec, physics (risk area), needs research into the current tire model before a plan is possible.

**"Fix the crash when the vehicle disconnects mid-mission."**
Route: Full. Unknown cause, protocol and state handling (risk area). Research first: reproduce and find the failing path.

## Plan step: vague vs executable

Vague (an executor will guess):
```
### S3: Add unit conversion [T1]
- Make the telemetry panel support imperial units.
```

Executable:
```
### S3: Add unit conversion to telemetry formatter [T1] [status: todo]
- Files: src/telemetry/formatter.py, tests/test_formatter.py
- Change: Add `format_speed(mps: float, units: Literal["metric","imperial"]) -> str`.
  metric → f"{mps*3.6:.1f} km/h"; imperial → f"{mps*2.23694:.1f} mph".
  Replace the two direct km/h conversions in `TelemetryFormatter.row()` with calls to it,
  passing `self.settings.units`.
- Acceptance: `pytest tests/test_formatter.py -q` passes, including new cases:
  0 m/s, 10 m/s metric (36.0 km/h), 10 m/s imperial (22.4 mph).
- Depends on: S1 (settings.units exists)
```

## Executor brief

```
You are executing one step of a larger plan. You won't see the rest of the conversation;
everything you need is here.

STEP: S3: Add unit conversion to telemetry formatter
[step text from PLAN.md, verbatim]

CONTEXT:
- settings.units already exists (added in S1) and is "metric" or "imperial".
- TelemetryFormatter.row() is at formatter.py lines 40–62; the two conversions are the `* 3.6` lines.
- Project uses pytest; tests live in tests/, one file per module.

KNOWN DEAD ENDS: none for this step.

DO NOT: change any file not listed, or change public signatures other than adding format_speed.

WHEN DONE: run `pytest tests/test_formatter.py -q`. Reply with:
1. What you changed (2–4 lines)
2. Files touched
3. Last 15 lines of the test output
4. Anything surprising
```

## Handoff entries

```
## Test log
- 2026-11-09 S3 PASS `pytest tests/test_formatter.py -q` (12 passed)
- 2026-11-09 S4 FAIL `pytest tests/test_panel.py -q`: AssertionError: expected "36.0 km/h", got "36.0 km/h " (trailing space from label padding)

## Dead ends
- S4: tried stripping whitespace in format_speed → breaks column alignment in the CSV export, which relies on padding. Fix belongs in TelemetryPanel.label(), not the formatter. Don't retry the formatter fix.

## Decisions
- Conversion factors hard-coded in format_speed rather than a units library: only two units needed, avoids a dependency.

## Learnings
- CSV export depends on fixed-width padding from formatter output; changing formatter whitespace breaks it. → promote to the project record (Learnings)
```

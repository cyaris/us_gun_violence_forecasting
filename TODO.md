# TODO

Action items from the repository retrospective audit (2026-08-04). Nothing here has been implemented yet.

## Critical

- [ ] Fix moving-average alignment in `frontend/src/lib/forecastData.js` (`movingAverage`). The `sma` package
      returns trailing averages aligned to the end of each window, but the code assigns `averages[0]` back to the
      *earliest* date instead of the date the window ends on. This shifts every smoothed series `range - 1` days
      earlier and drops the most recent `range - 1` days instead of the earliest ones. Active by default (initial
      moving-average window is 10 days). Add a Vitest unit test for `movingAverage`/`buildSeriesRows` asserting
      correct trailing alignment before fixing.
- [ ] Add `rel="noopener noreferrer"` to the Gun Violence Archive link in `frontend/src/lib/components/Tool.svelte`
      (currently the only `target="_blank"` link in the app missing it).

## Reliability

- [ ] Replace the fixed 365-row offset used for "Avg Yearly Trend" in `modelMetrics`
      (`frontend/src/lib/forecastData.js`) with true calendar-year lookback, since leap years (2016, 2020, 2024)
      cause a one-day misalignment.

## Test coverage

- [ ] Add `backend/tests/` covering `future_dataframe_lengths`, `load_daily_harmed`, and `prepare_for_visualization`
      in `backend/src/update_forecast_data.py`. `pytest` is already configured and declared as a dev dependency but
      currently collects zero tests.
- [ ] Add a test runner (Vitest) and unit tests for the pure functions in `frontend/src/lib/forecastData.js`
      (`movingAverage`, `modelMetrics`, `buildSeriesRows`).

## Cleanup

- [ ] Remove the stale commented-out planning notes in `frontend/src/routes/documentation/+page.svelte`.

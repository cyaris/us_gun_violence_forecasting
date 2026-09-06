import assert from "node:assert/strict"
import test from "node:test"

import { modelMetrics, movingAverage, previousCalendarYearDate } from "../src/lib/forecastData.js"

test("movingAverage aligns each result with the row that completes its finite-value window", () => {
  assert.deepEqual(movingAverage([{ value: 1 }, { value: 2 }, { value: 3 }, { value: 4 }], "value", 3), [
    null,
    null,
    2,
    3
  ])
  assert.deepEqual(movingAverage([{ value: 1 }, { value: null }, { value: 3 }, { value: 5 }], "value", 2), [
    null,
    null,
    2,
    4
  ])
})

test("previousCalendarYearDate preserves the calendar date with a February 29 fallback", () => {
  assert.equal(previousCalendarYearDate("2024-03-01"), "2023-03-01")
  assert.equal(previousCalendarYearDate("2024-02-29"), "2023-02-28")
  assert.equal(previousCalendarYearDate("2025-02-28"), "2024-02-28")
})

test("modelMetrics uses the February 28 value for a leap-day yearly trend", () => {
  let predictionField = "predicted_victims_2024"
  let chartRows = [
    { date: "2023-02-28", [predictionField]: 10 },
    { date: "2024-02-29", observed_victims: 14, [predictionField]: 14 }
  ]
  let rows = [{ d: chartRows[1], i: 1 }]

  assert.equal(
    modelMetrics({
      chartRows,
      forecastIndexedRows: rows,
      isFutureTimeframe: true,
      latestObservedYear: 2024,
      minYear: 2014,
      numObservations: 1,
      observedIndexedRows: [],
      year: 2024
    }).trend,
    "4"
  )
})

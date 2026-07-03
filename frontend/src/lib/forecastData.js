import sma from "sma"

export function parseLocalDate(date) {
  return new Date(`${date}T00:00:00`)
}

export function yearFromDate(d) {
  return Number(d.date.slice(0, 4))
}

export function predictionColumn(year) {
  return `predicted_victims_${year}`
}

export function finiteValue(value) {
  return value != null && Number.isFinite(Number(value))
}

export function movingAverage(rows, field, range) {
  if (!range) return rows.map(d => d[field])

  let values = Array(rows.length).fill(null)
  let finiteEntries = rows
    .map((row, i) => ({ i, value: row[field] }))
    .filter(({ value }) => finiteValue(value))
    .map(({ i, value }) => ({ i, value: Number(value) }))

  if (!finiteEntries.length) return values

  let averages = sma(
    finiteEntries.map(d => d.value),
    range
  ).map(v => parseFloat(v))

  finiteEntries.forEach(({ i }, averageIndex) => {
    values[i] = averages[averageIndex]
  })

  return values
}

export function buildSeriesRows({ rows, field, range = 0, observedOnly = false }) {
  rows = observedOnly ? rows.filter(d => !d.is_forecast) : rows
  let values = movingAverage(rows, field, range)

  return values.map((value, i) => ({ ...rows[i], value })).filter(d => finiteValue(d.value))
}

export function modelMetrics({
  year,
  isFutureTimeframe,
  chartRows,
  observedIndexedRows,
  forecastIndexedRows,
  minYear,
  latestObservedYear,
  numObservations,
}) {
  let predictionColumnName = predictionColumn(year)
  let rows = isFutureTimeframe ? forecastIndexedRows : observedIndexedRows

  let predSum = rows.reduce((sum, { d }) => sum + (d[predictionColumnName] ?? 0), 0)
  let yearlyTrends = rows
    .map(({ i }) => {
      let current = chartRows[i]?.[predictionColumnName]
      let previousYear = chartRows[i - 365]?.[predictionColumnName]

      return current != null && previousYear != null ? current - previousYear : null
    })
    .filter(finiteValue)
  let trendSum = yearlyTrends.reduce((sum, d) => sum + d, 0)

  let result = {
    input:
      year == latestObservedYear
        ? `${minYear}–${latestObservedYear}`
        : year == minYear
          ? `${minYear}`
          : `${minYear}–${year}`,
    total: Math.round(predSum).toLocaleString(),
    perDay: Math.round(predSum / rows.length).toLocaleString(),
    trend: Math.round(trendSum / yearlyTrends.length).toLocaleString(),
  }

  if (!isFutureTimeframe) {
    result.rmse = Math.round(
      Math.sqrt(
        rows.reduce((sum, { d }) => sum + ((d[predictionColumnName] ?? 0) - d.observed_victims) ** 2, 0) /
          numObservations
      )
    ).toLocaleString()
  }

  return result
}

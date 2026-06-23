<script>
  import * as d3 from "d3"
  import { interpolateString } from "d3-interpolate"
  import { format } from "date-fns"
  import sma from "sma"
  import { cubicInOut } from "svelte/easing"
  import { tweened } from "svelte/motion"
  import { CheckboxFilter, InfoIcon, Select, Slider } from "svelte-lib/components"
  import { drawCanvasCircles } from "svelte-lib/functions"

  import data from "../static/data.json"

  // Backend emits this time series chronologically; row order is used for yearly trend calculations.
  let parseLocalDate = date => new Date(`${date}T00:00:00`)
  let yearFromDate = d => Number(d.date.slice(0, 4))
  let predictionColumn = year => `predicted_victims_${year}`
  let observedVictimsColumn = "observed_victims"
  let observedVictimsMovingAverageColumn = `${observedVictimsColumn}_moving_average`
  let minYear = Math.min(...data.map(yearFromDate))
  let latestObservedYear = Math.max(...data.filter(d => !d.is_forecast).map(yearFromDate))
  let overallPredictionColumn = predictionColumn(latestObservedYear)
  let overallPredictionMovingAverageColumn = `${overallPredictionColumn}_moving_average`

  let width
  let viewportHeight
  let svgWidth
  let chartViewportWidth
  let svgHeight
  let graphStrokeWidth = 1
  let axisStrokeInset = graphStrokeWidth / 2

  let xScale
  let yScale
  let xAxisWidth
  // margins around the plot, matching the proportions of the original d3 project.
  let plotMargin = { top: 20, right: 20, bottom: 93, left: 84 }
  let yAxisMaskWidth = plotMargin.left - axisStrokeInset
  // the height of the x axis ticks.
  let xTickHeight = 10
  // the vertical distance between each xTick and xTick label.
  let xTickVerticalOffset = 8.5
  // the font size for the x tick labels.
  let xTickLabelSize = 14
  let yAxisTitleLeftPadding = 8
  let xTickLabelBandHeight = xTickLabelSize + 4
  let yAxisInfoX = 12 + yAxisTitleLeftPadding
  let chartColors = { observations: "#708090", overallModel: "orange", comparativeModel: "#00c07f" }
  let pointRadius = 4
  let observationCircleStroke = { color: "black", width: 0.5 }

  let filteredData

  let pathGeneratorFor

  let fadeClasses = "transition-opacity duration-300 ease-[cubic-bezier(0.65,0,0.35,1)]"
  let tweenTiming = { duration: 600, easing: cubicInOut }
  let observationsCanvas
  let timeSeriesCanvas
  let comparativeCanvas
  let animatedPointYScale = null

  let animatedYDomain = tweened([0, 1], {
    interpolate: (a, b) => {
      let min = d3.interpolateNumber(a[0], b[0])
      let max = d3.interpolateNumber(a[1], b[1])

      return t => [min(t), max(t)]
    },
    ...tweenTiming,
  })

  let animatedPaths = tweened(
    { observations: null, timeSeries: null },
    {
      interpolate: (a, b) => {
        let observations = interpolateString(a.observations, b.observations)
        let timeSeries = interpolateString(a.timeSeries, b.timeSeries)

        return t => ({
          observations: observations(t),
          timeSeries: timeSeries(t),
        })
      },
      ...tweenTiming,
    }
  )

  $: observationValueColumn = sliders.observations ? observedVictimsMovingAverageColumn : observedVictimsColumn
  $: timeSeriesValueColumn = sliders.timeSeries ? overallPredictionMovingAverageColumn : overallPredictionColumn
  $: timeSeriesPathFilterColumn = sliders.timeSeries ? timeSeriesValueColumn : observedVictimsColumn

  $: {
    if (width && viewportHeight) {
      chartViewportWidth = width * 0.7
      svgHeight = Math.max(plotMargin.top + plotMargin.bottom, Math.min(viewportHeight * 0.65, chartViewportWidth / 2))
      svgWidth = data.length * 0.4 + plotMargin.left + plotMargin.right + graphStrokeWidth * 2
      xAxisWidth = svgWidth - plotMargin.right - plotMargin.left - graphStrokeWidth * 2

      if (data.length) {
        filteredData = [...data]
          .sort((a, b) => b.observed_victims - a.observed_victims)
          .slice(checkboxFilters.lasVegasScale ? 0 : 1)
          .sort((a, b) => a.date.localeCompare(b.date))
          .map(d => ({ ...d, parsedDate: parseLocalDate(d.date) }))

        let getMovingAverage = function (field, range) {
          return sma(
            filteredData.filter(v => v[field]).map(v => v[field]),
            range
          ).map(v => parseFloat(v))
        }

        let observationsMovingAverage = getMovingAverage(observedVictimsColumn, sliders.observations)
        let timeSeries = getMovingAverage(overallPredictionColumn, sliders.timeSeries)
        // TODO: fix process so it is not based on an iterator, otherwise it will be wrong when items (last vegas) are filtered out.
        filteredData.forEach((d, i) => {
          d[observedVictimsMovingAverageColumn] = observationsMovingAverage[i]
          d[overallPredictionMovingAverageColumn] = timeSeries[i]
        })

        xScale = d3.scaleTime(
          d3.extent(filteredData, d => d.parsedDate),
          [0, xAxisWidth]
        )

        let yDomain = [0, d3.max(filteredData, d => Math.max(d[observationValueColumn], d[timeSeriesValueColumn]))]

        yScale = d3.scaleLinear(yDomain, [svgHeight - plotMargin.bottom, plotMargin.top])

        animatedYDomain.set(yDomain)

        pathGeneratorFor = function (field) {
          return d3
            .line()
            .curve(d3.curveNatural)
            .x(d => xScale(d.parsedDate))
            .y(d => yScale(d[field]))
        }
      }

      animatedPaths.set({
        observations: pathGeneratorFor(observationValueColumn)(filteredData.filter(v => v[observationValueColumn])),
        timeSeries: pathGeneratorFor(timeSeriesValueColumn)(filteredData.filter(v => v[timeSeriesPathFilterColumn])),
      })
    }
  }

  let selectItems = [
    { value: "Historical Data", label: "Historical Data" },
    { value: "Next 365 Days", label: "Next 365 Days" },
  ]

  let selectValue = selectItems[0]

  let sliderStep = 5

  let checkboxFilters = { lasVegasScale: true, displayObservations: true, displayModels: true }

  let sliders = { observations: 0, timeSeries: 10 }

  let checkboxFilterItems = [
    { key: "lasVegasScale", label: "Scale to Include the Las Vegas Shooting", tooltipKey: "lasVegasScale" },
    { key: "displayObservations", label: "Display Daily Observations" },
    { key: "displayModels", label: "Display Time Series Models" },
  ]

  let sliderItems = [
    { key: "observations", label: "Moving Average for Daily Observations", tooltipKey: "observationsSlider" },
    { key: "timeSeries", label: "Moving Average for Time Series Models", tooltipKey: "timeSeriesSlider" },
  ]

  let forecastDayCount = data.filter(d => d.is_forecast).length
  let forecastStartDate = data.find(d => d.is_forecast).date

  let firstDate = format(parseLocalDate(data[0].date), "M/d/yy")

  let hoverYear = null

  $: legendItems = [
    {
      key: "observations",
      label: "Daily Observations",
      color: chartColors.observations,
      visible: checkboxFilters.displayObservations,
      aggregated: sliders.observations > 0,
    },
    {
      key: "overallModel",
      label: "Overall Model",
      color: chartColors.overallModel,
      visible: checkboxFilters.displayModels,
      aggregated: sliders.timeSeries > 0,
    },
    {
      key: "comparativeModel",
      label: "Comparative Model",
      color: chartColors.comparativeModel,
      visible: checkboxFilters.displayModels && hoverYear != null && hoverYear < latestObservedYear,
      aggregated: sliders.timeSeries > 0,
    },
  ]

  let numObservations = data.filter(d => !d.is_forecast).length

  let plotGroup
  let comparativePath = null

  $: observationPointsVisible = checkboxFilters.displayObservations && sliders.observations == 0
  $: observationPathVisible = checkboxFilters.displayObservations && sliders.observations > 0
  $: timeSeriesPointsVisible = checkboxFilters.displayModels && sliders.timeSeries == 0
  $: timeSeriesPathVisible = checkboxFilters.displayModels && sliders.timeSeries > 0
  $: comparativePointsVisible = comparing && checkboxFilters.displayModels && sliders.timeSeries == 0
  $: comparativePathVisible = comparing && checkboxFilters.displayModels && sliders.timeSeries > 0

  $: animatedPointYScale =
    svgHeight && $animatedYDomain
      ? d3.scaleLinear($animatedYDomain, [svgHeight - plotMargin.bottom, plotMargin.top])
      : null

  $: plotBottomY = yScale ? yScale(0) : 0
  $: plotHeight = yScale ? plotBottomY - plotMargin.top : 0
  $: yAxisCenterY = plotBottomY ? (plotMargin.top + plotBottomY) / 2 : 0
  $: forecastStartX = xScale ? xScale(parseLocalDate(forecastStartDate)) : 0
  $: xTicks = xScale ? xScale.ticks() : []
  $: xTickLabelBandTop = plotBottomY ? plotBottomY + xTickHeight + xTickVerticalOffset : 0
  $: xTickLabelBandBottom = xTickLabelBandTop + xTickLabelBandHeight
  $: xAxisTitleX = chartViewportWidth ? plotMargin.left + (chartViewportWidth - plotMargin.left) / 2 : 0
  $: xAxisClipWidth = xAxisWidth ? xAxisWidth + axisStrokeInset : 0

  $: {
    let pointLayerReady = xScale && animatedPointYScale && svgWidth && svgHeight
    let pointLayerHoverHighlightWidth = comparing ? hoverHighlightWidth : null

    if (pointLayerReady) {
      let drawChartPointLayer = ({ canvas, rows, field, color, stroke = null }) =>
        drawCanvasCircles({
          canvas,
          rows,
          width: svgWidth,
          height: svgHeight,
          radius: pointRadius,
          color,
          stroke,
          getX: row => plotMargin.left + xScale(row.parsedDate),
          getY: row => animatedPointYScale(row[field]),
          isFaded: row =>
            pointLayerHoverHighlightWidth != null && xScale(row.parsedDate) > pointLayerHoverHighlightWidth,
        })

      drawChartPointLayer({
        canvas: observationsCanvas,
        rows: filteredData ? filteredData.filter(d => d.observed_victims) : [],
        field: "observed_victims",
        color: chartColors.observations,
        stroke: observationCircleStroke,
      })
      drawChartPointLayer({
        canvas: timeSeriesCanvas,
        rows: filteredData ? filteredData.filter(d => d[overallPredictionColumn]) : [],
        field: overallPredictionColumn,
        color: chartColors.overallModel,
      })
      drawChartPointLayer({
        canvas: comparativeCanvas,
        rows: comparing && filteredData ? filteredData.filter(d => d[predictionColumn(hoverYear)]) : [],
        field: comparing ? predictionColumn(hoverYear) : null,
        color: chartColors.comparativeModel,
      })
    }
  }

  let movingAverage = (rows, field, range) =>
    sma(
      rows.filter(v => v[field]).map(v => v[field]),
      range
    ).map(v => parseFloat(v))

  function yearlyTrendAt(rowIndex, field) {
    let current = data[rowIndex]?.[field]
    let previousYear = data[rowIndex - 365]?.[field]

    return current != null && previousYear != null ? current - previousYear : null
  }

  function modelMetrics(year, isFutureTimeframe) {
    let predictionColumnName = predictionColumn(year)
    let rows = data.map((d, i) => ({ d, i })).filter(({ d }) => (isFutureTimeframe ? d.is_forecast : !d.is_forecast))

    let predSum = rows.reduce((sum, { d }) => sum + (d[predictionColumnName] || 0), 0)
    let yearlyTrends = rows.map(({ i }) => yearlyTrendAt(i, predictionColumnName)).filter(v => v != null)
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
          rows.reduce((sum, { d }) => sum + ((d[predictionColumnName] || 0) - d.observed_victims) ** 2, 0) /
            numObservations
        )
      ).toLocaleString()
    }

    return result
  }

  function clearHover() {
    hoverYear = null
  }

  function handleHover(e) {
    let [pointerX] = d3.pointer(e, plotGroup)
    let year = xScale.invert(pointerX).getFullYear()

    if (year != hoverYear) {
      hoverYear = year
    }
  }

  $: comparing = hoverYear != null && hoverYear < latestObservedYear
  $: hoverHighlightWidth =
    comparing && xScale ? Math.min(xScale(parseLocalDate(`${hoverYear + 1}-01-01`)), xAxisWidth) : 0
  $: isFuture = selectValue.value == "Next 365 Days"

  $: overallMetrics = filteredData ? modelMetrics(latestObservedYear, isFuture) : null
  $: comparativeMetrics = comparing ? modelMetrics(hoverYear, isFuture) : null

  $: metricRows = [
    { label: "Model Input", key: "input" },
    { label: "Total Victims", key: "total" },
    { label: "Avg Victims per Day", key: "perDay" },
    { label: "Avg Yearly Trend", key: "trend", rounded: true },
    ...(isFuture ? [] : [{ label: "RMSE", key: "rmse", rounded: true }]),
  ]

  $: tooltipText = {
    lasVegasScale:
      "The Las Vegas shooting is the deadliest mass shooting in US history. With 548 total victims killed/injured, it is a major outlier in this dataset. Filter to see how this observation affects the scaling of the entire graph.",
    xAxis: "Individual incidents are summed together and grouped by date.",
    yAxis:
      "Includes all victims reported as injured or killed. Victims with unreported health statuses are not included.",
    observationsSlider:
      "Adjust the slider to specify a moving average for displaying daily observations. Units are in days, with 0 days displaying the actual/recorded observation.",
    timeSeriesSlider:
      "Adjust the slider to specify a moving average for displaying time series models. Units are in days, with 0 days displaying the exact prediction on a given day.",
    timeframe: `Use dropdown to compare time series model predictions for dates that took place in the past, or, take place in the next year (${forecastDayCount} days).`,
    metrics: isFuture
      ? `Model Input: What years of data were used to generate these predictions?\n\nTotal Victims: How many total victims does the model think there will be in the next ${forecastDayCount} days?\n\nAvg Victims per Day: How many victims does the model think there will be daily for the next ${forecastDayCount} days?\n\nAvg Yearly Trend: What is the average change between these predictions annually?`
      : `Model Input: What years of data were used to generate these predictions?\n\nTotal Victims: How many total victims does the model think there have been since ${firstDate}?\n\nAvg Victims per Day: How many victims does the model think there have been daily since ${firstDate}?\n\nAvg Yearly Trend: What is the average change between these predictions annually?\n\nRMSE: How do these predictions compare to the actual number of victims recorded daily since ${firstDate}?`,
  }

  $: {
    if (comparing && sliders.timeSeries && filteredData && xScale && yScale) {
      let movingAverages = movingAverage(filteredData, predictionColumn(hoverYear), sliders.timeSeries)

      comparativePath = d3
        .line()
        .curve(d3.curveNatural)
        .x(d => xScale(d.parsedDate))
        .y(d => yScale(d.value))(
        filteredData
          .map((d, i) => ({ parsedDate: d.parsedDate, value: movingAverages[i] }))
          .filter(d => d.value != null && !isNaN(d.value))
      )
    } else {
      comparativePath = null
    }
  }
</script>

<svelte:window bind:innerHeight={viewportHeight} />
<div
  class="flex h-full w-full flex-col items-center justify-center"
  bind:clientWidth={width}
>
  <div class="px-8 text-center text-lg min-[1300px]:hidden">This visualization is best viewed on a larger screen.</div>
  <div class="hidden min-[1300px]:block">
    {#if filteredData}
      <div class="relative mb-3 mt-4 text-sm" style="width:{chartViewportWidth}px">
        <div class="flex flex-col items-start">
          {#each checkboxFilterItems as checkbox (checkbox.key)}
            <div class="flex items-center gap-2">
              <CheckboxFilter
                labelClasses="font-medium"
                label={checkbox.label}
                value={checkboxFilters[checkbox.key]}
                selection={checkboxFilters[checkbox.key] ? [true] : []}
                deselection={checkboxFilters[checkbox.key] ? [] : [true]}
                on:update={({ detail: e }) => (checkboxFilters = { ...checkboxFilters, [checkbox.key]: !e.value })}
              />
              {#if checkbox.tooltipKey}
                <InfoIcon title={tooltipText[checkbox.tooltipKey]} tooltipClasses="max-w-80" />
              {/if}
            </div>
          {/each}
        </div>
        <span
          class="pointer-events-none absolute bottom-0 left-1/2 -translate-x-1/2 whitespace-nowrap text-sm"
          class:italic={comparing}
        >
          {comparing ? "Comparing Historical Forecasts..." : "Hover to Compare Historical Forecasts"}
        </span>
      </div>
      {#if svgWidth && svgHeight}
        <div
          class="relative w-full overflow-hidden border border-solid border-black"
          style="max-width:{chartViewportWidth}px"
        >
          <div class="w-full overflow-y-hidden overflow-x-scroll" style="height:{svgHeight}px">
            <div class="relative" style="width:{svgWidth}px; height:{svgHeight}px">
              <svg class="pointer-events-none absolute left-0 top-0 z-0" width={svgWidth} height={svgHeight}>
                {#if comparing}
                  <g transform="translate({plotMargin.left}, {0})">
                    <rect
                      class="non-reactive"
                      x={0}
                      y={plotMargin.top}
                      width={hoverHighlightWidth}
                      height={plotHeight}
                      fill="black"
                      fill-opacity={0.04}
                    />
                  </g>
                {/if}
              </svg>
              <canvas
                bind:this={observationsCanvas}
                class="pointer-events-none absolute left-0 top-0 z-10 {fadeClasses}"
                class:opacity-0={!observationPointsVisible}
                aria-hidden="true"
                style="width:{svgWidth}px; height:{svgHeight}px"
              />
              <canvas
                bind:this={timeSeriesCanvas}
                class="pointer-events-none absolute left-0 top-0 z-10 {fadeClasses}"
                class:opacity-0={!timeSeriesPointsVisible}
                aria-hidden="true"
                style="width:{svgWidth}px; height:{svgHeight}px"
              />
              <canvas
                bind:this={comparativeCanvas}
                class="pointer-events-none absolute left-0 top-0 z-10 {fadeClasses}"
                class:opacity-90={comparativePointsVisible}
                class:opacity-0={!comparativePointsVisible}
                aria-hidden="true"
                style="width:{svgWidth}px; height:{svgHeight}px"
              />
              <svg class="absolute left-0 top-0 z-20" width={svgWidth} height={svgHeight} id="graph">
                <g
                  bind:this={plotGroup}
                  transform="translate({plotMargin.left}, {0})"
                  role="presentation"
                  on:mousemove={handleHover}
                  on:mouseleave={clearHover}
                >
                  <rect x={0} y={plotMargin.top} width={xAxisWidth} height={plotHeight} fill="transparent" />
                  {#if comparing}
                    <path
                      class="non-reactive"
                      d="M0,{plotMargin.top}H{hoverHighlightWidth}V{plotBottomY}H0"
                      fill="transparent"
                      stroke="black"
                      stroke-width={1}
                    />
                  {/if}
                  <rect
                    class="non-reactive"
                    x={forecastStartX}
                    y={plotMargin.top}
                    width={xAxisWidth - forecastStartX}
                    height={plotHeight}
                    fill="black"
                    opacity={0.06}
                  />
                  <line
                    class="non-reactive"
                    stroke="black"
                    stroke-dasharray="4 4"
                    x1={forecastStartX}
                    x2={forecastStartX}
                    y1={plotMargin.top}
                    y2={plotBottomY}
                  />
                  <line
                    class="non-reactive"
                    stroke="black"
                    stroke-dasharray="1 4"
                    stroke-linecap="round"
                    x1={forecastStartX}
                    x2={xAxisWidth}
                    y1={plotMargin.top}
                    y2={plotMargin.top}
                  />
                  <path
                    class={observationPathVisible ? `${fadeClasses} hover:stroke-4` : `${fadeClasses} non-reactive`}
                    class:opacity-0={!observationPathVisible}
                    fill="transparent"
                    stroke={chartColors.observations}
                    stroke-width={3}
                    d={$animatedPaths.observations}
                  />
                  <path
                    class={timeSeriesPathVisible ? `${fadeClasses} hover:stroke-4` : `${fadeClasses} non-reactive`}
                    class:opacity-0={!timeSeriesPathVisible}
                    fill="transparent"
                    stroke={chartColors.overallModel}
                    stroke-width={3}
                    d={$animatedPaths.timeSeries}
                  />
                  {#if comparing && checkboxFilters.displayModels}
                    <path
                      class="non-reactive {fadeClasses}"
                      fill="transparent"
                      stroke={chartColors.comparativeModel}
                      stroke-width={3}
                      class:opacity-90={comparativePathVisible}
                      class:opacity-0={!comparativePathVisible}
                      d={comparativePath}
                    />
                  {/if}
                  <text
                    class="non-reactive fill-chart-1 text-sm italic"
                    x={(forecastStartX + xAxisWidth) / 2}
                    y={plotMargin.top + 22}
                    text-anchor="middle"
                  >
                    Next {forecastDayCount.toLocaleString()} days...
                  </text>
                </g>
                <svg
                  class="non-reactive text-sm"
                  x={yAxisMaskWidth}
                  y={plotBottomY}
                  width={xAxisClipWidth}
                  height={xTickHeight + 1}
                  overflow="hidden"
                >
                  <path
                    class="stroke-chart-1"
                    fill="transparent"
                    opacity={0.7}
                    d="M{axisStrokeInset},0V0H{xAxisClipWidth}V0"
                  />
                  {#each xTicks as xTick (xTick)}
                    <g transform="translate({xScale(xTick) + axisStrokeInset}, {0})">
                      <line class="stroke-chart-1" opacity={0.7} y1={0.5} y2={xTickHeight} />
                    </g>
                  {/each}
                </svg>
                <g class="non-reactive text-sm" transform="translate({plotMargin.left}, {plotBottomY})">
                  {#each xTicks as xTick (xTick)}
                    <text
                      class="fill-chart-1"
                      x={xScale(xTick)}
                      y={xTickHeight + xTickVerticalOffset + xTickLabelSize}
                      text-anchor="middle"
                    >
                      {xTick.getFullYear()}
                    </text>
                  {/each}
                </g>
              </svg>
            </div>
          </div>
          <svg class="pointer-events-none absolute left-0 top-0 z-30" width={chartViewportWidth} height={svgHeight}>
            <g class="non-reactive text-sm" transform="translate({plotMargin.left + 8}, {plotMargin.top + 12})">
              {#each legendItems as item, i (item.key)}
                <g transform="translate(0, {i * 16})">
                  {#if !item.visible}
                    <text class="fill-chart-1" x={8} dy="0.32em" text-anchor="middle">∅</text>
                  {:else if item.aggregated}
                    <line stroke={item.color} stroke-width={3.5} x1={0} x2={16} y1={0} y2={0} />
                  {:else}
                    <circle
                      fill={item.color}
                      stroke={item.key == "observations" ? observationCircleStroke.color : "none"}
                      stroke-width={item.key == "observations" ? observationCircleStroke.width : 0}
                      cx={8}
                      cy={0}
                      r={4}
                    />
                  {/if}
                  <text class="fill-chart-1" x={24} dy="0.32em">{item.label}</text>
                </g>
              {/each}
            </g>
          </svg>
          <div
            class="pointer-events-none absolute left-0 top-0 z-30 bg-white"
            style="width:{yAxisMaskWidth}px; height:{xTickLabelBandTop}px"
          />
          <div
            class="pointer-events-none absolute left-0 z-30 bg-white"
            style="top:{xTickLabelBandTop}px; width:{Math.max(
              plotMargin.left - 32,
              0
            )}px; height:{xTickLabelBandHeight}px"
          />
          <div
            class="pointer-events-none absolute left-0 z-30 bg-white"
            style="top:{xTickLabelBandBottom}px; width:{yAxisMaskWidth}px; height:{svgHeight - xTickLabelBandBottom}px"
          />
          <svg class="absolute left-0 top-0 z-40" width={yAxisMaskWidth} height={svgHeight} overflow="visible">
            <rect width={yAxisMaskWidth} height={plotBottomY} fill="white" pointer-events="none" />
            <g class="non-reactive text-sm" transform="translate({plotMargin.left}, {0})">
              <path class="stroke-chart-1" fill="transparent" opacity={0.7} d="M0,{plotMargin.top}V{plotBottomY}" />
              {#each yScale.ticks() as yTick (yTick)}
                <g transform="translate(0, {yScale(yTick)})">
                  <line class="stroke-chart-1" opacity={0.7} x1={-xTickHeight} x2={0} />
                  <text class="fill-chart-1" x={-xTickHeight - 4} dy="0.32em" text-anchor="end">
                    {yTick.toLocaleString()}
                  </text>
                </g>
              {/each}
            </g>
            <text
              class="non-reactive fill-chart-1 text-lg"
              text-anchor="middle"
              transform="translate({16 + yAxisTitleLeftPadding}, {yAxisCenterY}) rotate(-90)"
            >
              Total Victims
            </text>
            <g transform="rotate(-90, {yAxisInfoX}, {yAxisCenterY - 78})">
              <InfoIcon title={tooltipText.yAxis} tooltipClasses="max-w-80" cx={yAxisInfoX} cy={yAxisCenterY - 78} />
            </g>
          </svg>
          <svg class="pointer-events-none absolute left-0 top-0 z-20" width={chartViewportWidth} height={svgHeight}>
            <text class="non-reactive fill-chart-1 text-lg" text-anchor="middle" x={xAxisTitleX} y={svgHeight - 24}>
              Date
            </text>
            <g class="pointer-events-auto">
              <InfoIcon title={tooltipText.xAxis} tooltipClasses="max-w-80" cx={xAxisTitleX + 36} cy={svgHeight - 30} />
            </g>
          </svg>
        </div>
      {/if}
      <div class="mt-5 flex w-full items-start gap-8 text-sm" style="max-width:{chartViewportWidth}px">
        <div>
          <div class="mb-2 flex items-center gap-2 whitespace-nowrap font-medium">
            Prediction Timeframe
            <InfoIcon title={tooltipText.timeframe} tooltipClasses="max-w-80" />
          </div>
          <div class="w-36">
            <Select
              items={selectItems}
              value={selectValue}
              clearable={false}
              centeredValue={true}
              centeredItems={true}
              on:valueChange={({ detail: e }) => (selectValue = e.d)}
            />
          </div>
        </div>
        <table class="w-96 table-fixed border-collapse">
          <colgroup>
            <col class="w-48" />
            <col class="w-20" />
            <col class="w-28" />
          </colgroup>
          <thead>
            <tr>
              <th class="border-b-[3.5px] border-b-chart-1 pb-1 text-left align-bottom [border-bottom-style:solid]">
                <div class="flex items-center gap-2 font-medium">
                  Metrics
                  <InfoIcon title={tooltipText.metrics} tooltipClasses="max-w-80" />
                </div>
              </th>
              <th
                class="whitespace-nowrap border-b-[3.5px] pb-1 pl-3 pr-px text-right align-bottom font-medium [border-bottom-style:solid]"
                style:border-bottom-color={chartColors.overallModel}>Overall<br />Model</th
              >
              <th
                class="whitespace-nowrap border-b-[3.5px] pb-1 pl-3 pr-px text-right align-bottom font-medium [border-bottom-style:solid]"
                style:border-bottom-color={chartColors.comparativeModel}>Comparative<br />Model</th
              >
            </tr>
          </thead>
          <tbody>
            {#each metricRows as row (row.key)}
              <tr>
                <td class="whitespace-nowrap"
                  >{row.label}{#if row.rounded}&nbsp;<em>(Rounded)</em>{/if}</td
                >
                <td class="text-right">{overallMetrics ? overallMetrics[row.key] : ""}</td>
                <td class="text-right">{comparativeMetrics ? comparativeMetrics[row.key] : "—"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
        <div class="mt-4 grid grow grid-cols-2 gap-8">
          {#each sliderItems as slider (slider.key)}
            <div>
              <div class="ml-3.5 max-w-full text-left font-medium">
                {slider.label}
                <span class="inline-block w-0.5" />
                <InfoIcon title={tooltipText[slider.tooltipKey]} tooltipClasses="max-w-80" />
              </div>
              <Slider
                wrapperClasses="w-full"
                value={sliders[slider.key]}
                step={sliderStep}
                min={0}
                max={30}
                labelStep={sliderStep}
                labelEveryXTicks={2}
                float={true}
                labels={true}
                middle={true}
                on:valueChange={({ detail: e }) => (sliders = { ...sliders, [slider.key]: e.d })}
              />
            </div>
          {/each}
        </div>
      </div>
    {/if}
    <div class="mt-12" style="max-width:{chartViewportWidth}px">
      <p>
        All data compiled by <a href="https://gunviolencearchive.org" target="_blank">Gun Violence Archive (GVA)</a>, a
        not-for-profit corporation formed in 2013 to provide online public access to accurate information about
        gun-related violence in the United States.
      </p>
    </div>
  </div>
</div>

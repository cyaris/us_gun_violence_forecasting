<script>
  import { extent } from "d3-array"
  import { interpolateNumber } from "d3-interpolate"
  import { scaleLinear, scaleTime } from "d3-scale"
  import { pointer } from "d3-selection"
  import { curveNatural, line } from "d3-shape"
  import { format } from "date-fns"
  import { onMount } from "svelte"
  import { cubicInOut } from "svelte/easing"
  import { tweened } from "svelte/motion"
  import { CheckboxFilter, InfoIcon, Loading, Select, Slider } from "svelte-lib/components"
  import { createAnimationLoop, drawCanvasCircles, easeCubicInOut, getEasedProgress } from "svelte-lib/functions"
  import { configureCanvas2D, getCanvasPointerPoint } from "svelte-lib/functions/canvas"

  import {
    buildSeriesRows,
    finiteValue,
    modelMetrics,
    parseLocalDate,
    predictionColumn,
    yearFromDate
  } from "../forecastData.js"
  import data from "../static/data.json"

  let baseRows = [...data]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map(d => ({ ...d, parsedDate: parseLocalDate(d.date) }))
  let indexedRows = baseRows.map((d, i) => ({ d, i }))
  let observedRows = baseRows.filter(d => !d.is_forecast)
  let forecastRows = baseRows.filter(d => d.is_forecast)
  let observedIndexedRows = indexedRows.filter(({ d }) => !d.is_forecast)
  let forecastIndexedRows = indexedRows.filter(({ d }) => d.is_forecast)
  let observedVictimsColumn = "observed_victims"
  let minYear = Math.min(...baseRows.map(yearFromDate))
  let maxYear = Math.max(...baseRows.map(yearFromDate))
  let latestObservedYear = Math.max(...observedRows.map(yearFromDate))
  let overallPredictionColumn = predictionColumn(latestObservedYear)

  let windowWidth
  let viewportHeight
  let lastDevicePixelRatio
  let svgWidth
  let graphStrokeWidth = 1
  let axisStrokeInset = graphStrokeWidth / 2

  let xScale
  let yScale
  let xAxisWidth
  // margins around the plot, matching the proportions of the original d3 project.
  let plotMargin = { top: 20, right: 20, bottom: 79, left: 79 }
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
  let chartLayout = { viewportWidth: 0, height: 0 }

  let chartRows = baseRows

  let fadeClasses = "transition-opacity duration-300 ease-[cubic-bezier(0.65,0,0.35,1)]"
  let tweenTiming = { duration: 600, easing: cubicInOut }
  let observationsCanvas
  let timeSeriesCanvas
  let comparativeCanvas
  let linesCanvas
  let hoverPoint = null
  let animatedYScale = null
  let scrollContainer
  let scrollLeft = 0
  let scrollViewportWidth = 0
  let observationSeriesRows = []
  let overallModelSeriesRows = []
  let comparativeSeriesRows = []
  let comparativeSeriesCache = new Map()
  let modelMetricsCache = new Map()

  let animatedYDomain = tweened([0, 1], {
    interpolate: (a, b) => {
      let min = interpolateNumber(a[0], b[0])
      let max = interpolateNumber(a[1], b[1])

      return t => [min(t), max(t)]
    },
    ...tweenTiming
  })

  function interpolateSeriesRows(previousRows, nextRows) {
    let previousValues = new Map((previousRows || []).map(d => [+d.parsedDate, d.value]))
    let interpolators = (nextRows || []).map(d => {
      let previousValue = previousValues.get(+d.parsedDate)
      let previousValueIsFinite = previousValue != null && Number.isFinite(Number(previousValue))
      let pointValue = interpolateNumber(
        previousValueIsFinite ? Number(previousValue) : Number(d.value),
        Number(d.value)
      )

      return { ...d, pointValue }
    })

    return progress => interpolators.map(({ pointValue, ...d }) => ({ ...d, value: pointValue(progress) }))
  }

  function createSeriesLineAnimation() {
    let interpolator = () => []
    let start = 0
    let duration = 0

    function getProgress(now) {
      return duration > 0 ? getEasedProgress({ duration, ease: easeCubicInOut, now, start }) : 1
    }

    function getCurrentRows(now) {
      return interpolator(getProgress(now))
    }

    function isAnimating(now) {
      return getProgress(now) < 1
    }

    function set(rows, now, { instant = false } = {}) {
      interpolator = instant ? () => rows : interpolateSeriesRows(getCurrentRows(now), rows)
      start = now
      duration = instant ? 0 : tweenTiming.duration
    }

    return { getCurrentRows, isAnimating, set }
  }

  let observationsLineAnimation = createSeriesLineAnimation()
  let timeSeriesLineAnimation = createSeriesLineAnimation()
  let comparativeLineAnimation = createSeriesLineAnimation()

  let animatedComparativePoints = tweened([], {
    interpolate: (a, b) => {
      let previousValues = new Map((a || []).map(d => [+d.parsedDate, d.value]))
      let interpolators = (b || []).map(d => {
        let previousValue = previousValues.get(+d.parsedDate)
        let previousValueIsFinite = previousValue != null && Number.isFinite(Number(previousValue))
        let pointValue = interpolateNumber(
          previousValueIsFinite ? Number(previousValue) : Number(d.value),
          Number(d.value)
        )

        return { ...d, pointValue }
      })

      return t => interpolators.map(({ pointValue, ...d }) => ({ ...d, value: pointValue(t) }))
    },
    ...tweenTiming
  })

  let selectItems = [
    { value: "Historical Data", label: "Historical Data" },
    { value: "Next 365 Days", label: "Next 365 Days" }
  ]

  let selectValue = selectItems[0]

  let sliderItems = {
    xAxisDayWidth: [
      { value: "fit", label: "Fit" },
      { value: "narrow", label: "Narrow" },
      { value: "wide", label: "Wide" },
      { value: "wider", label: "Wider" },
      { value: "widest", label: "Widest" }
    ]
  }

  let sliderValue = { movingAverageWindow: 10, xAxisDayWidth: 0 }

  let checkboxFilters = { displayObservations: true, displayModels: true }

  let checkboxFilterItems = [
    { key: "displayObservations", label: "Display Daily Observations" },
    { key: "displayModels", label: "Display Time Series Models" }
  ]

  let forecastDayCount = forecastRows.length
  let forecastStartDate = forecastRows[0]?.date

  let firstDate = format(baseRows[0].parsedDate, "M/d/yy")

  let hoverYear = null

  let numObservations = observedRows.length

  let plotGroup

  function cachedComparativeSeriesRows(field, range) {
    let key = `${field}:${range}`

    if (!comparativeSeriesCache.has(key)) {
      comparativeSeriesCache.set(key, buildSeriesRows({ rows: chartRows, field, range }))
    }

    return comparativeSeriesCache.get(key)
  }

  function rowIsVisible(row, startX, endX) {
    let x = xScale(row.parsedDate)
    return x >= startX && x <= endX
  }

  $: comparing = hoverYear != null && hoverYear < latestObservedYear
  $: comparativePredictionColumn = comparing ? predictionColumn(hoverYear) : null
  $: hoverYearEndX =
    hoverYear != null && xScale ? Math.min(xScale(parseLocalDate(`${hoverYear + 1}-01-01`)), xAxisWidth) : null
  $: hoverHighlightWidth = comparing && hoverYearEndX != null ? hoverYearEndX : 0

  $: {
    observationSeriesRows = buildSeriesRows({
      rows: chartRows,
      field: observedVictimsColumn,
      range: sliderValue.movingAverageWindow,
      observedOnly: true
    })
    overallModelSeriesRows = buildSeriesRows({
      rows: chartRows,
      field: overallPredictionColumn,
      range: sliderValue.movingAverageWindow
    })
  }

  function syncViewportSize() {
    let devicePixelRatio = window.devicePixelRatio

    if (lastDevicePixelRatio == null || devicePixelRatio === lastDevicePixelRatio) {
      windowWidth = window.innerWidth
      viewportHeight = window.innerHeight
    }

    lastDevicePixelRatio = devicePixelRatio
  }

  onMount(syncViewportSize)

  $: {
    if (windowWidth && viewportHeight) {
      let compactViewportWidth = Math.max(windowWidth - 24, 0)

      chartLayout = {
        viewportWidth: windowWidth >= 1300 ? windowWidth * 0.7 : compactViewportWidth,
        height:
          windowWidth >= 1300
            ? Math.max(plotMargin.top + plotMargin.bottom, Math.min(viewportHeight * 0.625, (windowWidth * 0.7) / 2))
            : Math.max(320, Math.min(viewportHeight * 0.5, compactViewportWidth * 0.78))
      }
      let defaultXAxisWidth = baseRows.length * 0.4
      let fittedXAxisWidth = Math.max(
        (scrollViewportWidth || chartLayout.viewportWidth) - plotMargin.left - plotMargin.right - graphStrokeWidth * 2,
        0
      )

      xAxisWidth =
        sliderValue.xAxisDayWidth <= 2
          ? fittedXAxisWidth + ((defaultXAxisWidth - fittedXAxisWidth) * sliderValue.xAxisDayWidth) / 2
          : defaultXAxisWidth * (1 + (sliderValue.xAxisDayWidth - 2) * 0.1)
      svgWidth = xAxisWidth + plotMargin.left + plotMargin.right + graphStrokeWidth * 2

      xScale = scaleTime(
        extent(baseRows, d => d.parsedDate),
        [0, xAxisWidth]
      )
    }
  }

  $: visiblePlotStartX = Math.max(0, scrollLeft - plotMargin.left)
  $: visiblePlotEndX =
    xAxisWidth && chartLayout.viewportWidth
      ? Math.min(xAxisWidth, scrollLeft + (scrollViewportWidth || chartLayout.viewportWidth) - plotMargin.left)
      : 0

  $: {
    if (comparing && comparativePredictionColumn) {
      comparativeSeriesRows = cachedComparativeSeriesRows(comparativePredictionColumn, sliderValue.movingAverageWindow)
    } else {
      comparativeSeriesRows = []
    }
  }

  $: {
    if (chartRows && xScale && chartLayout.height) {
      let visibleMax = 0
      let addValue = value => {
        if (finiteValue(value)) visibleMax = Math.max(visibleMax, Number(value))
      }

      if (checkboxFilters.displayObservations) {
        observationSeriesRows
          .filter(d => rowIsVisible(d, visiblePlotStartX, visiblePlotEndX))
          .forEach(d => addValue(d.value))
      }

      if (checkboxFilters.displayModels) {
        overallModelSeriesRows
          .filter(d => rowIsVisible(d, visiblePlotStartX, visiblePlotEndX))
          .forEach(d => addValue(d.value))

        if (comparing) {
          comparativeSeriesRows
            .filter(d => rowIsVisible(d, visiblePlotStartX, visiblePlotEndX))
            .forEach(d => addValue(d.value))
        }
      }

      let yDomain = [0, visibleMax || 1]

      yScale = scaleLinear(yDomain, [chartLayout.height - plotMargin.bottom, plotMargin.top])

      animatedYDomain.set(yDomain)
    }
  }

  $: {
    if (chartRows && yScale) {
      let now = performance.now()

      observationsLineAnimation.set(observationSeriesRows, now)
      timeSeriesLineAnimation.set(overallModelSeriesRows, now)
      lineAnimationLoop.start()
    }
  }

  $: legendItems = [
    {
      key: "observations",
      label: "Daily Observations",
      color: chartColors.observations,
      visible: checkboxFilters.displayObservations,
      aggregated: sliderValue.movingAverageWindow > 0
    },
    {
      key: "overallModel",
      label: "Overall Model",
      color: chartColors.overallModel,
      visible: checkboxFilters.displayModels,
      aggregated: sliderValue.movingAverageWindow > 0
    },
    {
      key: "comparativeModel",
      label: "Comparative Model",
      color: chartColors.comparativeModel,
      visible: checkboxFilters.displayModels && hoverYear != null && hoverYear < latestObservedYear,
      aggregated: sliderValue.movingAverageWindow > 0
    }
  ]

  $: observationPointsVisible = checkboxFilters.displayObservations && sliderValue.movingAverageWindow == 0
  $: observationPathVisible = checkboxFilters.displayObservations && sliderValue.movingAverageWindow > 0
  $: timeSeriesPointsVisible = checkboxFilters.displayModels && sliderValue.movingAverageWindow == 0
  $: timeSeriesPathVisible = checkboxFilters.displayModels && sliderValue.movingAverageWindow > 0
  $: comparativePointsVisible = comparing && checkboxFilters.displayModels && sliderValue.movingAverageWindow == 0
  $: comparativePathVisible = comparing && checkboxFilters.displayModels && sliderValue.movingAverageWindow > 0
  $: lineVisibility = {
    comparative: comparing && checkboxFilters.displayModels && comparativePathVisible,
    observations: observationPathVisible,
    timeSeries: timeSeriesPathVisible
  }

  function drawSeriesLine(context, rows, color, hoverable) {
    if (rows.length < 2) return

    let path2D = new Path2D()
    line()
      .curve(curveNatural)
      .x(d => plotMargin.left + xScale(d.parsedDate))
      .y(d => animatedYScale(d.value))
      .context(path2D)(rows)

    context.strokeStyle = color
    context.lineWidth = 3

    if (hoverable && hoverPoint && context.isPointInStroke(path2D, hoverPoint.x, hoverPoint.y)) {
      context.lineWidth = 4
    }

    context.stroke(path2D)
  }

  function drawLinesCanvas(timestamp) {
    let { context } = configureCanvas2D({ canvas: linesCanvas, height: chartLayout.height, width: svgWidth })
    if (!context) return false

    context.clearRect(0, 0, svgWidth, chartLayout.height)

    if (lineVisibility.observations) {
      drawSeriesLine(context, observationsLineAnimation.getCurrentRows(timestamp), chartColors.observations, true)
    }
    if (lineVisibility.timeSeries) {
      drawSeriesLine(context, timeSeriesLineAnimation.getCurrentRows(timestamp), chartColors.overallModel, true)
    }
    if (lineVisibility.comparative) {
      drawSeriesLine(context, comparativeLineAnimation.getCurrentRows(timestamp), chartColors.comparativeModel, false)
    }

    return (
      observationsLineAnimation.isAnimating(timestamp) ||
      timeSeriesLineAnimation.isAnimating(timestamp) ||
      comparativeLineAnimation.isAnimating(timestamp)
    )
  }

  let lineAnimationLoop = createAnimationLoop(drawLinesCanvas)

  $: animatedYScale =
    chartLayout.height && $animatedYDomain
      ? scaleLinear($animatedYDomain, [chartLayout.height - plotMargin.bottom, plotMargin.top])
      : null

  $: if (linesCanvas && xScale && animatedYScale && svgWidth && chartLayout.height && lineVisibility) {
    lineAnimationLoop.start()
  }

  $: plotBottomY = yScale ? yScale(0) : 0
  $: plotHeight = yScale ? plotBottomY - plotMargin.top : 0
  $: yAxisTicks = yScale ? yScale.ticks() : []
  $: yAxisCenterY = chartLayout.height / 2
  // the distance from the y-axis title's center to its info icon, tuned per breakpoint to match the title's font size.
  $: yAxisTitleIconOffset = windowWidth >= 900 ? 65 : 59
  $: forecastStartX = xScale ? xScale(parseLocalDate(forecastStartDate)) : 0
  $: forecastLabelRotated = xAxisWidth - forecastStartX < 144
  $: forecastLabelX = (forecastStartX + xAxisWidth) / 2
  $: forecastLabelY = forecastLabelRotated ? plotMargin.top + plotHeight / 2 : plotMargin.top + 22
  $: xTickYearStep = xAxisWidth ? Math.max(1, Math.ceil(((maxYear - minYear) * 56) / xAxisWidth)) : 1
  $: xTicks = xScale
    ? Array.from({ length: maxYear - minYear + 1 }, (_, i) => parseLocalDate(`${minYear + i}-01-01`))
    : []
  $: xTickLabels = xTicks.filter((_, i) => i % xTickYearStep == 0)
  $: xTickLabelBandTop = plotBottomY ? plotBottomY + xTickHeight + xTickVerticalOffset : 0
  $: xTickLabelBandBottom = xTickLabelBandTop + xTickLabelBandHeight
  $: xAxisTitleX = chartLayout.viewportWidth / 2
  // the distance from the x-axis title's center to its info icon, tuned per breakpoint to match the title's font size.
  $: xAxisTitleIconOffset = windowWidth >= 900 ? 34 : 31.5
  $: xAxisClipWidth = xAxisWidth ? xAxisWidth + axisStrokeInset : 0

  $: {
    let pointLayerReady = xScale && animatedYScale && svgWidth && chartLayout.height
    let pointLayerHoverHighlightWidth = comparing ? hoverHighlightWidth : null

    if (pointLayerReady) {
      let pointIsPastHighlight = row =>
        pointLayerHoverHighlightWidth != null && xScale(row.parsedDate) > pointLayerHoverHighlightWidth
      let pointIsNeverFaded = () => false

      let drawChartPointLayer = ({
        canvas,
        rows,
        field,
        color,
        stroke = null,
        isFaded = pointIsPastHighlight,
        fadedAlpha = 0.5
      }) =>
        drawCanvasCircles({
          canvas,
          rows,
          width: svgWidth,
          height: chartLayout.height,
          radius: pointRadius,
          color,
          stroke,
          getX: row => plotMargin.left + xScale(row.parsedDate),
          getY: row => animatedYScale(row[field]),
          isFaded,
          fadedAlpha
        })

      drawChartPointLayer({
        canvas: observationsCanvas,
        rows: observationSeriesRows,
        field: "value",
        color: chartColors.observations,
        stroke: observationCircleStroke
      })
      drawChartPointLayer({
        canvas: timeSeriesCanvas,
        rows: overallModelSeriesRows,
        field: "value",
        color: chartColors.overallModel,
        isFaded: pointIsNeverFaded
      })
      drawChartPointLayer({
        canvas: comparativeCanvas,
        rows: $animatedComparativePoints,
        field: "value",
        color: chartColors.comparativeModel,
        isFaded: pointIsNeverFaded
      })
    }
  }

  function cachedModelMetrics(year, isFutureTimeframe) {
    let cacheKey = `${year}:${isFutureTimeframe}`

    if (modelMetricsCache.has(cacheKey)) {
      return modelMetricsCache.get(cacheKey)
    }

    let result = modelMetrics({
      year,
      isFutureTimeframe,
      chartRows,
      observedIndexedRows,
      forecastIndexedRows,
      minYear,
      latestObservedYear,
      numObservations
    })

    modelMetricsCache.set(cacheKey, result)

    return result
  }

  function handleHover(e) {
    let [pointerX] = pointer(e, plotGroup)
    let year = xScale.invert(pointerX).getFullYear()

    if (year != hoverYear) {
      hoverYear = year
    }

    hoverPoint = getCanvasPointerPoint(linesCanvas, e)
    lineAnimationLoop.start()
  }

  function handleHoverLeave() {
    hoverYear = null
    hoverPoint = null
    lineAnimationLoop.start()
  }

  $: isFuture = selectValue.value == "Next 365 Days"

  $: overallMetrics = chartRows ? cachedModelMetrics(latestObservedYear, isFuture) : null
  $: comparativeMetrics = comparing ? cachedModelMetrics(hoverYear, isFuture) : null

  $: metricRows = [
    { label: "Model Input", key: "input" },
    { label: "Total Victims", key: "total" },
    { label: "Avg Victims per Day", key: "perDay" },
    { label: "Avg Yearly Trend", key: "trend", rounded: true },
    ...(isFuture ? [] : [{ label: "RMSE", key: "rmse", rounded: true }])
  ]

  $: tooltipText = {
    xAxis: "Individual incidents are summed together and grouped by date.",
    yAxis:
      "Includes all victims reported as injured or killed. Victims with unreported health statuses are not included.",
    xAxisDayWidth:
      "Adjust the horizontal space occupied by each day. Drag left to show more dates at once or right to spread dates farther apart.",
    movingAverageWindow:
      "Adjust the slider to specify a moving average for all charted values. Units are in days, with 0 days displaying exact daily observations and predictions.",
    timeframe: `Use dropdown to compare time series model predictions for dates that took place in the past, or, take place in the next year (${forecastDayCount} days).`,
    metrics: isFuture
      ? `Model Input: What years of data were used to generate these predictions?\n\nTotal Victims: How many total victims does the model think there will be in the next ${forecastDayCount} days?\n\nAvg Victims per Day: How many victims does the model think there will be daily for the next ${forecastDayCount} days?\n\nAvg Yearly Trend: What is the average change between these predictions annually?`
      : `Model Input: What years of data were used to generate these predictions?\n\nTotal Victims: How many total victims does the model think there have been since ${firstDate}?\n\nAvg Victims per Day: How many victims does the model think there have been daily since ${firstDate}?\n\nAvg Yearly Trend: What is the average change between these predictions annually?\n\nRMSE: How do these predictions compare to the actual number of victims recorded daily since ${firstDate}?`
  }

  $: {
    let now = performance.now()

    if (comparing && sliderValue.movingAverageWindow && comparativeSeriesRows && xScale && yScale) {
      comparativeLineAnimation.set(comparativeSeriesRows, now)
    } else {
      comparativeLineAnimation.set([], now, { instant: true })
    }

    lineAnimationLoop.start()
  }

  $: {
    animatedComparativePoints.set(comparativePointsVisible ? comparativeSeriesRows : [])
  }
</script>

<svelte:window on:resize={syncViewportSize} />
<div class="flex h-full w-full flex-col items-center justify-center">
  <div class="box-border w-full px-3 py-4 min-[1300px]:px-0 min-[1300px]:py-0">
    {#if chartRows && svgWidth && chartLayout.height}
      <div
        class="relative mx-auto mb-3 mt-4 flex flex-col gap-2 text-sm min-[1300px]:block"
        style="max-width:{chartLayout.viewportWidth}px"
      >
        <div class="flex flex-col items-start">
          {#each checkboxFilterItems as checkbox (checkbox.key)}
            <div class="flex items-center gap-x-2">
              <CheckboxFilter
                labelClasses="mb-0 font-medium"
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
          class="hidden text-sm font-medium min-[1300px]:pointer-events-none min-[1300px]:absolute min-[1300px]:bottom-0 min-[1300px]:left-1/2 min-[1300px]:block min-[1300px]:-translate-x-1/2 min-[1300px]:whitespace-nowrap"
          class:italic={comparing}
        >
          {comparing ? "Comparing Historical Forecasts..." : "Hover to Compare Historical Forecasts"}
        </span>
      </div>
      {#if svgWidth && chartLayout.height}
        <div
          class="relative mx-auto w-full overflow-hidden border border-solid border-black"
          style="max-width:{chartLayout.viewportWidth}px"
        >
          <div
            bind:this={scrollContainer}
            bind:clientWidth={scrollViewportWidth}
            class="w-full overflow-y-hidden overflow-x-scroll"
            style="height:{chartLayout.height}px"
            on:scroll={() => (scrollLeft = scrollContainer?.scrollLeft || 0)}
          >
            <div class="relative" style="width:{svgWidth}px; height:{chartLayout.height}px">
              <svg class="pointer-events-none absolute left-0 top-0 z-0" width={svgWidth} height={chartLayout.height}>
                <g transform="translate({plotMargin.left}, {0})">
                  <rect
                    class="non-reactive"
                    x={forecastStartX}
                    y={plotMargin.top}
                    width={xAxisWidth - forecastStartX}
                    height={plotHeight}
                    fill="black"
                    opacity={0.06}
                  />
                </g>
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
                style="width:{svgWidth}px; height:{chartLayout.height}px"
              />
              <canvas
                bind:this={timeSeriesCanvas}
                class="pointer-events-none absolute left-0 top-0 z-10 {fadeClasses}"
                class:opacity-0={!timeSeriesPointsVisible}
                aria-hidden="true"
                style="width:{svgWidth}px; height:{chartLayout.height}px"
              />
              <canvas
                bind:this={comparativeCanvas}
                class="pointer-events-none absolute left-0 top-0 z-10 {fadeClasses}"
                class:opacity-0={!comparativePointsVisible}
                aria-hidden="true"
                style="width:{svgWidth}px; height:{chartLayout.height}px"
              />
              <canvas
                bind:this={linesCanvas}
                class="pointer-events-none absolute left-0 top-0 z-[15]"
                aria-hidden="true"
                style="width:{svgWidth}px; height:{chartLayout.height}px"
              />
              <svg class="absolute left-0 top-0 z-20" width={svgWidth} height={chartLayout.height} id="graph">
                <g
                  bind:this={plotGroup}
                  transform="translate({plotMargin.left}, {0})"
                  role="presentation"
                  on:mousemove={handleHover}
                  on:mouseleave={handleHoverLeave}
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
                  <text
                    class="non-reactive fill-chart-1 text-sm italic"
                    x={forecastLabelX}
                    y={forecastLabelY}
                    text-anchor="middle"
                    dominant-baseline={forecastLabelRotated ? "middle" : null}
                    transform={forecastLabelRotated ? `rotate(90, ${forecastLabelX}, ${forecastLabelY})` : null}
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
                  {#each xTickLabels as xTick (xTick)}
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
          <svg
            class="pointer-events-none absolute left-0 top-0 z-30"
            width={chartLayout.viewportWidth}
            height={chartLayout.height}
          >
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
            style="top:{xTickLabelBandBottom}px; width:{yAxisMaskWidth}px; height:{chartLayout.height -
              xTickLabelBandBottom}px"
          />
          <svg
            class="absolute left-0 top-0 z-40 overflow-visible"
            width={yAxisMaskWidth}
            height={chartLayout.height}
            overflow="visible"
          >
            <rect width={yAxisMaskWidth} height={plotBottomY} fill="white" pointer-events="none" />
            <g class="non-reactive text-sm" transform="translate({plotMargin.left}, {0})">
              <path class="stroke-chart-1" fill="transparent" opacity={0.7} d="M0,{plotMargin.top}V{plotBottomY}" />
              {#each yAxisTicks as yTick, i (yTick)}
                <g transform="translate(0, {animatedYScale ? animatedYScale(yTick) : yScale(yTick)})">
                  <line class="stroke-chart-1" opacity={0.7} x1={-xTickHeight} x2={0} />
                  {#if windowWidth >= 900 || (yAxisTicks.length - 1 - i) % 2 === 0}
                    <text class="fill-chart-1" x={-xTickHeight - 4} dy="0.32em" text-anchor="end">
                      {yTick.toLocaleString()}
                    </text>
                  {/if}
                </g>
              {/each}
            </g>
            <text
              class="non-reactive fill-chart-1 text-sm font-medium min-[900px]:text-base"
              text-anchor="middle"
              transform="translate({16 + yAxisTitleLeftPadding}, {yAxisCenterY}) rotate(-90)"
            >
              Total Victims
            </text>
            <g transform="rotate(-90, {yAxisInfoX}, {yAxisCenterY - yAxisTitleIconOffset})">
              <InfoIcon
                title={tooltipText.yAxis}
                tooltipClasses="max-w-80"
                cx={yAxisInfoX}
                cy={yAxisCenterY - yAxisTitleIconOffset}
              />
            </g>
          </svg>
          <svg
            class="pointer-events-none absolute left-0 top-0 z-20"
            width={chartLayout.viewportWidth}
            height={chartLayout.height}
          >
            <text
              class="non-reactive fill-chart-1 text-sm font-medium min-[900px]:text-base"
              text-anchor="middle"
              x={xAxisTitleX}
              y={chartLayout.height - 18}
            >
              Date
            </text>
            <g class="pointer-events-auto">
              <InfoIcon
                title={tooltipText.xAxis}
                tooltipClasses="max-w-80"
                cx={xAxisTitleX + xAxisTitleIconOffset}
                cy={chartLayout.height - 24}
              />
            </g>
          </svg>
        </div>
      {/if}
      <div
        class="mx-auto mt-5 grid w-full gap-y-5 text-sm min-[900px]:grid-cols-[9.875rem_minmax(18rem,22rem)_minmax(max-content,1fr)_minmax(max-content,1fr)] min-[900px]:items-start min-[900px]:gap-x-6"
        style="max-width:{chartLayout.viewportWidth}px"
      >
        {#if windowWidth >= 900}
          <div class="min-[900px]:col-start-1 min-[900px]:row-start-1">
            <div class="mb-2 flex items-center gap-2 whitespace-nowrap font-medium">
              Prediction Timeframe
              <InfoIcon title={tooltipText.timeframe} tooltipClasses="max-w-80" />
            </div>
            <div class="w-36">
              <Select
                items={selectItems}
                bind:value={selectValue}
                clearable={false}
                searchable={false}
                centeredValue={true}
                centeredItems={true}
                label="Prediction Timeframe"
                labelClasses="sr-only"
              />
            </div>
          </div>
          <div class="min-[900px]:col-start-4 min-[900px]:row-start-1">
            <div class="ml-3.5 flex items-center gap-2 whitespace-nowrap font-medium">
              Moving Average Window
              <InfoIcon title={tooltipText.movingAverageWindow} tooltipClasses="max-w-80" />
            </div>
            <Slider
              wrapperClasses="w-full"
              value={sliderValue.movingAverageWindow}
              step={5}
              suffix=" days"
              min={0}
              max={30}
              labelStep={2}
              float={true}
              labels={true}
              middle={true}
              on:valueChange={({ detail: e }) => (sliderValue = { ...sliderValue, movingAverageWindow: e.d })}
            />
          </div>
        {:else}
          <div class="flex items-start gap-8">
            <div class="w-36 shrink-0">
              <div class="mb-2 flex items-center gap-2 whitespace-nowrap font-medium">
                Prediction Timeframe
                <InfoIcon title={tooltipText.timeframe} tooltipClasses="max-w-80" />
              </div>
              <Select
                items={selectItems}
                bind:value={selectValue}
                clearable={false}
                searchable={false}
                centeredValue={true}
                centeredItems={true}
                label="Prediction Timeframe"
                labelClasses="sr-only"
              />
            </div>
            <div class="min-w-0 flex-1">
              <div class="ml-3.5 flex items-center gap-2 font-medium">
                Moving Average Window
                <InfoIcon title={tooltipText.movingAverageWindow} tooltipClasses="max-w-80" />
              </div>
              <Slider
                wrapperClasses="w-full"
                value={sliderValue.movingAverageWindow}
                step={5}
                suffix=" days"
                min={0}
                max={30}
                labelStep={2}
                float={true}
                labels={true}
                middle={true}
                on:valueChange={({ detail: e }) => (sliderValue = { ...sliderValue, movingAverageWindow: e.d })}
              />
            </div>
          </div>
        {/if}
        <div class="overflow-x-auto min-[900px]:col-start-2 min-[900px]:row-start-1">
          <table class="metrics-table min-w-full border-collapse whitespace-nowrap">
            <colgroup>
              <col class="w-[54%] min-[900px]:w-1/2" />
              <col class="w-[22%] min-[900px]:w-[21%]" />
              <col class="w-[24%] min-[900px]:w-[29%]" />
            </colgroup>
            <thead>
              <tr>
                <th
                  class="border-b-[3.5px] border-b-chart-1 pb-[5px] text-left align-bottom [border-bottom-style:solid]"
                >
                  <div class="flex items-center gap-2 font-medium">
                    Metrics
                    <InfoIcon title={tooltipText.metrics} tooltipClasses="max-w-80" />
                  </div>
                </th>
                <th
                  class="border-b-[3.5px] pb-[5px] pl-2 pr-px text-right align-bottom font-medium [border-bottom-style:solid]"
                  style:border-bottom-color={chartColors.overallModel}>Overall<br />Model</th
                >
                <th
                  class="border-b-[3.5px] pb-[5px] pl-2 pr-px text-right align-bottom font-medium [border-bottom-style:solid]"
                  style:border-bottom-color={chartColors.comparativeModel}>Comparative<br />Model</th
                >
              </tr>
            </thead>
            <tbody>
              {#each metricRows as row, i (row.key)}
                <tr>
                  <td class={i == 0 ? "pt-1" : ""}
                    >{row.label}{#if row.rounded}&nbsp;<em>(Rounded)</em>{/if}</td
                  >
                  <td class="{i == 0 ? 'pt-1' : ''} text-right">{overallMetrics ? overallMetrics[row.key] : ""}</td>
                  <td class="{i == 0 ? 'pt-1' : ''} text-right"
                    >{comparativeMetrics ? comparativeMetrics[row.key] : "—"}</td
                  >
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <div class="hidden min-[900px]:col-start-3 min-[900px]:row-start-1 min-[900px]:block">
          <div class="ml-3.5 flex items-center gap-2 whitespace-nowrap font-medium">
            Day Width
            <InfoIcon title={tooltipText.xAxisDayWidth} tooltipClasses="max-w-80" />
          </div>
          <Slider
            wrapperClasses="w-full"
            items={sliderItems.xAxisDayWidth}
            value={sliderValue.xAxisDayWidth}
            min={0}
            max={sliderItems.xAxisDayWidth.length - 1}
            labelStep={2}
            float={true}
            labels={true}
            middle={true}
            on:valueChange={({ detail: e }) => (sliderValue = { ...sliderValue, xAxisDayWidth: e.d })}
          />
        </div>
      </div>
      <div class="mx-auto mt-12" style="max-width:{chartLayout.viewportWidth}px">
        <p>
          All data compiled by <a href="https://gunviolencearchive.org" target="_blank">Gun Violence Archive (GVA)</a>,
          a not-for-profit corporation formed in 2013 to provide online public access to accurate information about
          gun-related violence in the United States.
        </p>
      </div>
    {:else}
      <div class="flex min-h-[50vh] w-full items-center justify-center">
        <Loading classes="h-16 w-16" image="circle" />
      </div>
    {/if}
  </div>
</div>

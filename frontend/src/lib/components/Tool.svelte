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
  import { drawCanvasCircles, getContrastingTextColor, getCSSColors } from "svelte-lib/functions"
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
  let observedIndexedRows = indexedRows.filter(({ d }) => !d.is_forecast)
  let forecastIndexedRows = indexedRows.filter(({ d }) => d.is_forecast)
  let observedRows = observedIndexedRows.map(({ d }) => d)
  let forecastRows = forecastIndexedRows.map(({ d }) => d)
  let minYear = Math.min(...baseRows.map(yearFromDate))
  let maxYear = Math.max(...baseRows.map(yearFromDate))
  let latestObservedYear = Math.max(...observedRows.map(yearFromDate))
  let toolRoot
  let chartColors = {}

  const chartColorProperties = {
    comparativeModel: "--data-color-2",
    observations: "--data-neutral",
    overallModel: "--data-color-1",
    surface: "--ui-surface"
  }

  let layoutWidth
  let viewportHeight
  let canvasPixelRatio = 1
  let lastPixelRatio
  let lastViewportWidth
  let svgWidth
  let graphStrokeWidth = 1
  let axisStrokeInset = graphStrokeWidth / 2

  let xScale
  let yScale
  let xAxisWidth
  // margins around the plot, matching the proportions of the original d3 project.
  let plotMargin
  let yAxisMaskWidth
  // the height of the x axis ticks.
  let xTickHeight = 10
  // the vertical distance between each xTick and xTick label.
  let xTickVerticalOffset = 8.5
  // the font size for the x tick labels.
  let xTickLabelSize = 14
  let yAxisTitleLeftPadding
  let xTickLabelBandHeight = xTickLabelSize + 4
  let yAxisInfoX
  let chartLayout = { viewportWidth: 0, height: 0 }

  $: observationCircleStroke = {
    color:
      chartColors.observations && chartColors.surface
        ? getContrastingTextColor(chartColors.observations, chartColors.surface)
        : "transparent",
    width: 0.5
  }

  let chartRows = baseRows

  let fadeClasses = "transition-opacity duration-300 ease-[cubic-bezier(0.65,0,0.35,1)]"
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

  function createPositionedRowsInterpolator(previousRows, nextRows) {
    let previousPositions = new Map((previousRows || []).map(d => [+d.parsedDate, d]))
    let interpolators = (nextRows || []).map(d => {
      let previousPosition = previousPositions.get(+d.parsedDate)

      return {
        ...d,
        interpolateX: interpolateNumber(previousPosition?.x ?? d.x, d.x),
        interpolateY: interpolateNumber(previousPosition?.y ?? d.y, d.y)
      }
    })

    return progress =>
      interpolators.map(({ interpolateX, interpolateY, ...d }) => ({
        ...d,
        x: interpolateX(progress),
        y: interpolateY(progress)
      }))
  }

  function createChartSceneInterpolator(previousScene, nextScene) {
    let interpolateComparativePointRows = createPositionedRowsInterpolator(
      previousScene.comparativePointRows,
      nextScene.comparativePointRows
    )
    let interpolateLineRows = Object.fromEntries(
      Object.entries(nextScene.lineRows).map(([key, rows]) => [
        key,
        createPositionedRowsInterpolator(previousScene.lineRows[key], rows)
      ])
    )
    let interpolateYDomain = nextScene.yDomain.map((value, i) => interpolateNumber(previousScene.yDomain[i], value))

    return progress => ({
      comparativePointRows: interpolateComparativePointRows(progress),
      lineRows: Object.fromEntries(
        Object.entries(interpolateLineRows).map(([key, interpolateRows]) => [key, interpolateRows(progress)])
      ),
      yDomain: interpolateYDomain.map(interpolateValue => interpolateValue(progress))
    })
  }

  let animatedChartScene = tweened(
    { comparativePointRows: [], lineRows: { comparative: [], observations: [], timeSeries: [] }, yDomain: [0, 1] },
    { duration: 600, easing: cubicInOut, interpolate: createChartSceneInterpolator }
  )

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

  let forecastDayCount = forecastRows.length

  let firstDate = format(baseRows[0].parsedDate, "M/d/yy")

  let hoverYear = null
  let comparativeYear = null

  let plotGroup

  $: compactLayout = layoutWidth < 900
  $: wideLayout = layoutWidth >= 1300

  $: plotMargin = compactLayout
    ? { top: 12, right: 12, bottom: 71, left: 74 }
    : { top: 20, right: 20, bottom: 79, left: 79 }
  $: yAxisMaskWidth = plotMargin.left - axisStrokeInset
  $: yAxisTitleLeftPadding = compactLayout ? 3 : 8
  $: yAxisInfoX = 12 + yAxisTitleLeftPadding

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

  function comparisonHighlightWidth(year) {
    return year != null && xScale ? Math.min(xScale(parseLocalDate(`${year + 1}-01-01`)), xAxisWidth) : 0
  }

  $: comparing = comparativeYear != null
  $: comparativePredictionColumn = comparing ? predictionColumn(comparativeYear) : null
  $: comparativeHighlightWidth = comparisonHighlightWidth(comparativeYear)
  $: hoveredComparisonYear = hoverYear != null && hoverYear != comparativeYear ? hoverYear : null
  $: hoveredComparisonHighlightWidth = comparisonHighlightWidth(hoveredComparisonYear)

  $: {
    observationSeriesRows = buildSeriesRows({
      rows: chartRows,
      field: "observed_victims",
      range: sliderValue.movingAverageWindow,
      observedOnly: true
    })
    overallModelSeriesRows = buildSeriesRows({
      rows: chartRows,
      field: predictionColumn(latestObservedYear),
      range: sliderValue.movingAverageWindow
    })
  }

  function syncLayoutSize() {
    let pixelRatio = window.devicePixelRatio
    // Browser zoom scales the reported viewport by the inverse device pixel ratio, measured against the sizes the
    // layout was last committed at; a real viewport change (e.g. resizing the window, or moving it to a monitor with
    // a different scale factor) does not match that prediction.
    let zoomOnly =
      lastPixelRatio != null &&
      pixelRatio !== lastPixelRatio &&
      Math.abs(window.innerWidth - (lastViewportWidth * lastPixelRatio) / pixelRatio) <= 2

    canvasPixelRatio = pixelRatio

    if (zoomOnly) return

    layoutWidth = toolRoot.clientWidth
    viewportHeight = window.innerHeight
    lastPixelRatio = pixelRatio
    lastViewportWidth = window.innerWidth
  }

  onMount(() => {
    let observer = new ResizeObserver(syncLayoutSize)
    observer.observe(toolRoot)

    return () => observer.disconnect()
  })

  onMount(() => (chartColors = getCSSColors(chartColorProperties, toolRoot)))

  $: {
    if (layoutWidth && viewportHeight) {
      let compactViewportWidth = Math.max(layoutWidth - 24, 0)

      chartLayout = {
        viewportWidth: wideLayout ? layoutWidth * 0.7 : compactViewportWidth,
        height: wideLayout
          ? Math.max(plotMargin.top + plotMargin.bottom, Math.min(viewportHeight * 0.625, (layoutWidth * 0.7) / 2))
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

      yScale = scaleLinear([0, visibleMax || 1], [chartLayout.height - plotMargin.bottom, plotMargin.top])
    }
  }

  $: legendItems = [
    {
      key: "observations",
      label: "Observations",
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
      visible: checkboxFilters.displayModels && comparing,
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
    comparative: comparativePathVisible,
    observations: observationPathVisible,
    timeSeries: timeSeriesPathVisible
  }

  function positionSeriesRows(rows) {
    return rows.map(d => ({ ...d, x: plotMargin.left + xScale(d.parsedDate), y: yScale(d.value) }))
  }

  $: if (chartRows && xScale && yScale) {
    animatedChartScene.set({
      comparativePointRows: comparativePointsVisible ? positionSeriesRows(comparativeSeriesRows) : [],
      lineRows: {
        comparative: comparativePathVisible ? positionSeriesRows(comparativeSeriesRows) : [],
        observations: positionSeriesRows(observationSeriesRows),
        timeSeries: positionSeriesRows(overallModelSeriesRows)
      },
      yDomain: yScale.domain()
    })
  }

  function drawSeriesLine(context, { color, hoverable, rows }, currentHoverPoint) {
    if (rows.length < 2) return

    let path2D = new Path2D()
    line()
      .curve(curveNatural)
      .x(d => d.x)
      .y(d => d.y)
      .context(path2D)(rows)

    context.strokeStyle = color
    context.lineWidth = 3

    if (hoverable && currentHoverPoint && context.isPointInStroke(path2D, currentHoverPoint.x, currentHoverPoint.y)) {
      context.lineWidth = 4
    }

    context.stroke(path2D)
  }

  function getLineScene(lineRows, visibility) {
    return [
      {
        color: chartColors.observations,
        hoverable: true,
        rows: lineRows.observations,
        visible: visibility.observations
      },
      { color: chartColors.overallModel, hoverable: true, rows: lineRows.timeSeries, visible: visibility.timeSeries },
      {
        color: chartColors.comparativeModel,
        hoverable: false,
        rows: lineRows.comparative,
        visible: visibility.comparative
      }
    ].filter(({ visible }) => visible)
  }

  function drawLinesCanvas(lineRows, visibility, currentHoverPoint) {
    let { context } = configureCanvas2D({ canvas: linesCanvas, height: chartLayout.height, width: svgWidth })
    if (!context) return

    context.clearRect(0, 0, svgWidth, chartLayout.height)
    context.save()
    getLineScene(lineRows, visibility).forEach(layer => drawSeriesLine(context, layer, currentHoverPoint))
    context.restore()
  }

  $: animatedYScale =
    chartLayout.height && $animatedChartScene.yDomain
      ? scaleLinear($animatedChartScene.yDomain, [chartLayout.height - plotMargin.bottom, plotMargin.top])
      : null

  $: if (canvasPixelRatio && linesCanvas && svgWidth && chartLayout.height && chartColors.observations) {
    drawLinesCanvas($animatedChartScene.lineRows, lineVisibility, hoverPoint)
  }

  $: plotBottomY = yScale ? yScale(0) : 0
  $: plotHeight = yScale ? plotBottomY - plotMargin.top : 0
  $: yAxisTicks = yScale ? yScale.ticks() : []
  $: yAxisCenterY = chartLayout.height / 2
  // the distance from the y-axis title's center to its info icon, tuned per breakpoint to match the title's font size.
  $: yAxisTitleIconOffset = compactLayout ? 59 : 65
  $: forecastStartX = xScale ? xScale(parseLocalDate(forecastRows[0]?.date)) : 0
  $: forecastLabelRotated = xAxisWidth - forecastStartX < 144
  $: forecastLabelX = (forecastStartX + xAxisWidth) / 2
  $: forecastLabelY = forecastLabelRotated ? plotMargin.top + plotHeight / 2 : plotMargin.top + 22
  $: xTickYearStep = xAxisWidth ? Math.max(1, Math.ceil(((maxYear - minYear) * 56) / xAxisWidth)) : 1
  $: xTicks = xScale
    ? Array.from({ length: maxYear - minYear + 1 }, (_, i) => parseLocalDate(`${minYear + i}-01-01`))
    : []
  $: xTickLabelItems = xTicks.map((date, i) => ({
    date,
    x: xScale(date),
    year: date.getFullYear(),
    visible: xTickYearStep == 1 || i % xTickYearStep == 0
  }))
  $: xTickLabelBandTop = plotBottomY ? plotBottomY + xTickHeight + xTickVerticalOffset : 0
  $: xTickLabelBandBottom = xTickLabelBandTop + xTickLabelBandHeight
  $: xAxisTitleX = chartLayout.viewportWidth / 2
  $: xAxisTitleBottomOffset = compactLayout ? 10 : 18
  // the distance from the x-axis title's center to its info icon, tuned per breakpoint to match the title's font size.
  $: xAxisTitleIconOffset = compactLayout ? 31.5 : 34
  $: xAxisClipWidth = xAxisWidth ? xAxisWidth + axisStrokeInset : 0

  $: {
    let pointLayerReady =
      canvasPixelRatio && xScale && animatedYScale && svgWidth && chartLayout.height && chartColors.observations

    if (pointLayerReady) {
      let pointIsPastHighlight = row => comparing && xScale(row.parsedDate) > comparativeHighlightWidth
      let pointIsNeverFaded = () => false

      let drawChartPointLayer = ({
        canvas,
        color,
        fadedAlpha = 0.5,
        field,
        getX = row => plotMargin.left + xScale(row.parsedDate),
        getY = row => animatedYScale(row[field]),
        isFaded = pointIsPastHighlight,
        rows,
        stroke = null
      }) =>
        drawCanvasCircles({
          canvas,
          rows,
          width: svgWidth,
          height: chartLayout.height,
          radius: 4,
          color,
          stroke,
          getX,
          getY,
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
        rows: $animatedChartScene.comparativePointRows,
        color: chartColors.comparativeModel,
        getX: row => row.x,
        getY: row => row.y,
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
      numObservations: observedRows.length
    })

    modelMetricsCache.set(cacheKey, result)

    return result
  }

  function comparativeYearAtPointer(e) {
    let [pointerX] = pointer(e, plotGroup)
    let year = xScale.invert(pointerX).getFullYear()

    return year >= minYear && year < latestObservedYear ? year : null
  }

  function toggleComparativeYear(year) {
    if (year == null) return

    comparativeYear = comparativeYear == year ? null : year
  }

  function handleHover(e) {
    let year = comparativeYearAtPointer(e)

    if (year != hoverYear) hoverYear = year

    hoverPoint = getCanvasPointerPoint(linesCanvas, e)
  }

  function handleHoverLeave() {
    hoverYear = null
    hoverPoint = null
  }

  $: isFuture = selectValue.value == "Next 365 Days"

  $: overallMetrics = chartRows ? cachedModelMetrics(latestObservedYear, isFuture) : null
  $: comparativeMetrics = comparing ? cachedModelMetrics(comparativeYear, isFuture) : null

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
</script>

<svelte:window
  on:resize={syncLayoutSize}
  on:palettechange={() => (chartColors = getCSSColors(chartColorProperties, toolRoot))}
/>
<div class="data-palette flex h-full w-full flex-col items-center justify-center" bind:this={toolRoot}>
  <div
    class="box-border self-start {wideLayout ? '' : 'px-3 py-4'}"
    class:w-full={!layoutWidth}
    style:width={layoutWidth ? `${layoutWidth}px` : null}
  >
    {#if chartRows && svgWidth && chartLayout.height}
      <div
        class="relative mx-auto mb-3 mt-4 text-sm {wideLayout ? 'block' : 'flex flex-col gap-2'}"
        style="max-width:{chartLayout.viewportWidth}px"
      >
        <div class="flex flex-col items-start">
          <CheckboxFilter
            labelClasses="mb-0 font-medium"
            label="Observations"
            value={checkboxFilters.displayObservations}
            selection={checkboxFilters.displayObservations ? [true] : []}
            deselection={checkboxFilters.displayObservations ? [] : [true]}
            on:update={({ detail: e }) => (checkboxFilters = { ...checkboxFilters, displayObservations: !e.value })}
          />
          <CheckboxFilter
            labelClasses="mb-0 font-medium"
            label="Time Series Models"
            value={checkboxFilters.displayModels}
            selection={checkboxFilters.displayModels ? [true] : []}
            deselection={checkboxFilters.displayModels ? [] : [true]}
            on:update={({ detail: e }) => (checkboxFilters = { ...checkboxFilters, displayModels: !e.value })}
          />
        </div>
        {#if !comparing && wideLayout}
          <span
            class="pointer-events-none absolute bottom-0 left-1/2 -translate-x-1/2 whitespace-nowrap text-sm font-medium"
          >
            Click a Region to Compare Historical Forecasts
          </span>
        {/if}
      </div>
      {#if svgWidth && chartLayout.height}
        <div
          class="relative mx-auto w-full overflow-hidden border border-solid border-chart-line"
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
                    class="non-reactive fill-chart-band"
                    x={forecastStartX}
                    y={plotMargin.top}
                    width={xAxisWidth - forecastStartX}
                    height={plotHeight}
                  />
                </g>
                {#if comparing}
                  <g transform="translate({plotMargin.left}, {0})">
                    <rect
                      class="non-reactive fill-chart-band-subtle"
                      x={0}
                      y={plotMargin.top}
                      width={comparativeHighlightWidth}
                      height={plotHeight}
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
                  on:click={e => toggleComparativeYear(comparativeYearAtPointer(e))}
                >
                  <rect
                    class="cursor-pointer"
                    x={0}
                    y={plotMargin.top}
                    width={xAxisWidth}
                    height={plotHeight}
                    fill="transparent"
                  />
                  {#if comparing}
                    <path
                      class="non-reactive stroke-chart-line"
                      data-comparative-highlight
                      d="M0,{plotMargin.top}H{comparativeHighlightWidth}V{plotBottomY}H0"
                      fill="transparent"
                      stroke-width={1}
                    />
                  {/if}
                  {#if hoveredComparisonYear != null}
                    <path
                      class="non-reactive stroke-chart-line"
                      data-hover-highlight
                      d="M0,{plotMargin.top}H{hoveredComparisonHighlightWidth}V{plotBottomY}H0"
                      fill="transparent"
                      stroke-width={1}
                    />
                  {/if}
                  <line
                    class="non-reactive stroke-chart-line"
                    stroke-dasharray="4 4"
                    x1={forecastStartX}
                    x2={forecastStartX}
                    y1={plotMargin.top}
                    y2={plotBottomY}
                  />
                  <line
                    class="non-reactive stroke-chart-line"
                    stroke-dasharray="1 4"
                    stroke-linecap="round"
                    x1={forecastStartX}
                    x2={xAxisWidth}
                    y1={plotMargin.top}
                    y2={plotMargin.top}
                  />
                  <text
                    class="non-reactive fill-ui-text text-sm italic"
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
                  <path class="stroke-chart-line" fill="transparent" d="M{axisStrokeInset},0V0H{xAxisClipWidth}V0" />
                  {#each xTickLabelItems as item (item.date)}
                    <g transform="translate({item.x + axisStrokeInset}, {0})">
                      <line class="stroke-chart-line" y1={0.5} y2={xTickHeight} />
                    </g>
                  {/each}
                </svg>
                <g class="non-reactive text-sm" transform="translate({plotMargin.left}, {plotBottomY})">
                  {#each xTickLabelItems as item (item.date)}
                    <text
                      class="fill-ui-text"
                      class:hidden={!item.visible}
                      x={item.x}
                      y={xTickHeight + xTickVerticalOffset + xTickLabelSize}
                      text-anchor="middle"
                    >
                      {item.year}
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
                    <text class="fill-ui-text" x={8} dy="0.32em" text-anchor="middle">∅</text>
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
                  <text class="fill-ui-text" x={24} dy="0.32em">{item.label}</text>
                </g>
              {/each}
            </g>
          </svg>
          <div
            class="pointer-events-none absolute left-0 top-0 z-30 bg-ui-surface"
            style="width:{yAxisMaskWidth}px; height:{xTickLabelBandTop}px"
          />
          <div
            class="pointer-events-none absolute left-0 z-30 bg-ui-surface"
            style="top:{xTickLabelBandTop}px; width:{Math.max(
              plotMargin.left - 32,
              0
            )}px; height:{xTickLabelBandHeight}px"
          />
          <div
            class="pointer-events-none absolute left-0 z-30 bg-ui-surface"
            style="top:{xTickLabelBandBottom}px; width:{yAxisMaskWidth}px; height:{chartLayout.height -
              xTickLabelBandBottom}px"
          />
          <svg
            class="absolute left-0 top-0 z-40 overflow-visible"
            width={yAxisMaskWidth}
            height={chartLayout.height}
            overflow="visible"
          >
            <rect class="fill-ui-surface" width={yAxisMaskWidth} height={plotBottomY} pointer-events="none" />
            <g class="non-reactive text-sm" transform="translate({plotMargin.left}, {0})">
              <path class="stroke-chart-line" fill="transparent" d="M0,{plotMargin.top}V{plotBottomY}" />
              {#each yAxisTicks as yTick, i (yTick)}
                <g transform="translate(0, {animatedYScale ? animatedYScale(yTick) : yScale(yTick)})">
                  <line class="stroke-chart-line" x1={-xTickHeight} x2={0} />
                  {#if !compactLayout || (yAxisTicks.length - 1 - i) % 2 === 0}
                    <text class="fill-ui-text" x={-xTickHeight - 4} dy="0.32em" text-anchor="end">
                      {yTick.toLocaleString()}
                    </text>
                  {/if}
                </g>
              {/each}
            </g>
            <text
              class="non-reactive fill-ui-text font-medium {compactLayout ? 'text-sm' : 'text-base'}"
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
              class="non-reactive fill-ui-text font-medium {compactLayout ? 'text-sm' : 'text-base'}"
              text-anchor="middle"
              x={xAxisTitleX}
              y={chartLayout.height - xAxisTitleBottomOffset}
            >
              Date
            </text>
            <g class="pointer-events-auto">
              <InfoIcon
                title={tooltipText.xAxis}
                tooltipClasses="max-w-80"
                cx={xAxisTitleX + xAxisTitleIconOffset}
                cy={chartLayout.height - xAxisTitleBottomOffset - 6}
              />
            </g>
          </svg>
        </div>
      {/if}
      <div
        class="mx-auto mt-5 grid w-full gap-y-5 text-sm {compactLayout
          ? ''
          : 'grid-cols-[9.875rem_minmax(18rem,22rem)_minmax(max-content,1fr)_minmax(max-content,1fr)] items-start gap-x-6'}"
        style="max-width:{chartLayout.viewportWidth}px"
      >
        {#if !compactLayout}
          <div class="col-start-1 row-start-1">
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
          <div class="col-start-4 row-start-1">
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
        <div class="overflow-x-auto {compactLayout ? '' : 'col-start-2 row-start-1'}">
          <table class="metrics-table min-w-full border-collapse whitespace-nowrap">
            <colgroup>
              <col class={compactLayout ? "w-[54%]" : "w-1/2"} />
              <col class={compactLayout ? "w-[22%]" : "w-[21%]"} />
              <col class={compactLayout ? "w-[24%]" : "w-[29%]"} />
            </colgroup>
            <thead>
              <tr>
                <th
                  class="border-b-[3.5px] border-b-chart-line pb-[5px] text-left align-bottom [border-bottom-style:solid]"
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
        {#if !compactLayout}
          <div class="col-start-3 row-start-1">
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
        {/if}
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

<style>
  .data-palette {
    --data-color-1: oklch(from var(--data-palette-reference) 65% 0.14 calc(h - 120));
    --data-color-2: oklch(from var(--data-palette-reference) 65% 0.14 calc(h + 120));
    --data-neutral: color-mix(in srgb, var(--ui-text) 70%, var(--ui-surface));
  }
</style>

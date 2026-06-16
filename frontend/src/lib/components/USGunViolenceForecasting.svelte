<script>
  import * as d3 from "d3"
  import { interpolateString } from "d3-interpolate"
  import { format } from "date-fns"
  import sma from "sma"
  import { cubicInOut } from "svelte/easing"
  import { tweened } from "svelte/motion"
  import { CheckboxFilter, InfoIcon, InfoTooltip, Select, Slider, Text } from "svelte-lib/components"
  import { getTextWidth, tooltip } from "svelte-lib/functions"

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
  let height
  let svgWidth
  let chartViewportWidth
  let svgHeight
  let graphStrokeWidth = 1

  let xScale
  let yScale
  let xTickLength
  let xAxisWidth
  // margins around the plot, matching the proportions of the original d3 project.
  let plotMargin = { top: 20, right: 20, bottom: 65, left: 65 }
  // the height of the x axis ticks.
  let xTickHeight = 10
  // the vertical distance between each xTick and xTick label.
  let xTickVerticalOffset = 8.5
  // the font size for the x tick labels.
  let xTickLabelSize = 12

  // the full bottom band holding the x axis ticks, year labels, and "Date" title.
  let xAxisHeight = plotMargin.bottom

  let filteredData

  let pathGeneratorFor

  let pxPerDay = 0.4
  let fadeClasses = "transition-opacity duration-300 delay-100 ease-[cubic-bezier(0.65,0,0.35,1)]"
  let tweenTiming = {
    duration: 600,
    delay: 100,
    easing: cubicInOut,
  }
  let graphWidth
  let observationsCanvas
  let timeSeriesCanvas
  let comparativeCanvas
  let hoveredObservation = null
  let observationPointRows = []
  let timeSeriesPointRows = []
  let comparativePointRows = []
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
    if (width) {
      chartViewportWidth = width * 0.8
      graphWidth = data.length * pxPerDay
      svgHeight = height * 0.65
      svgWidth = graphWidth + plotMargin.left + plotMargin.right + graphStrokeWidth * 2
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

        let observationsMovingAverage = getMovingAverage(observedVictimsColumn, sliderItems[sliders.observations].label)
        let timeSeries = getMovingAverage(overallPredictionColumn, sliderItems[sliders.timeSeries].label)

        // TODO: fix process so it is not based on an iterator, otherwise it will be wrong when items (last vegas) are filtered out.
        filteredData.forEach((d, i) => {
          d[observedVictimsMovingAverageColumn] = observationsMovingAverage[i]
          d[overallPredictionMovingAverageColumn] = timeSeries[i]
        })

        xScale = d3.scaleTime(
          d3.extent(filteredData, d => d.parsedDate),
          [0, xAxisWidth]
        )

        xTickLength = xScale(xScale.ticks()[1]) - xScale(xScale.ticks()[0])

        let yDomain = [0, d3.max(filteredData, d => Math.max(d[observationValueColumn], d[timeSeriesValueColumn]))]

        yScale = d3.scaleLinear(yDomain, [svgHeight - xAxisHeight, plotMargin.top])

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
    { value: "Past - Present", label: `${minYear} - Present` },
    { value: "Next 365 Days", label: "Next 365 Days" },
  ]

  let selectValue = selectItems[0]

  let sliderItems = [
    { value: 0, label: 0 },
    { value: 1, label: 5 },
    { value: 2, label: 10 },
    { value: 3, label: 15 },
    { value: 4, label: 20 },
    { value: 5, label: 25 },
    { value: 6, label: 30 },
  ]

  let checkboxFilters = {
    lasVegasScale: true,
    displayObservations: true,
    displayModels: true,
  }

  let sliders = { observations: 0, timeSeries: 2 }

  let forecastDayCount = data.filter(d => d.is_forecast).length
  let forecastStartDate = data.find(d => d.is_forecast).date

  let firstDate = format(parseLocalDate(data[0].date), "M/d/yy")

  let hoverYear = null

  $: legendItems = [
    {
      label: "Daily Observations",
      color: "teal",
      visible: checkboxFilters.displayObservations,
      aggregated: sliders.observations > 0,
    },
    {
      label: "Overall Model",
      color: "orange",
      visible: checkboxFilters.displayModels,
      aggregated: sliders.timeSeries > 0,
    },
    {
      label: "Comparative Model",
      color: "#00c07f",
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
    svgHeight && $animatedYDomain ? d3.scaleLinear($animatedYDomain, [svgHeight - xAxisHeight, plotMargin.top]) : null

  $: observationPointRows = filteredData ? filteredData.filter(d => d.observed_victims) : []
  $: timeSeriesPointRows = filteredData ? filteredData.filter(d => d[overallPredictionColumn]) : []
  $: comparativePointRows = comparing && filteredData ? filteredData.filter(d => d[predictionColumn(hoverYear)]) : []

  $: drawPointLayer(
    observationsCanvas,
    observationPointRows,
    "observed_victims",
    "teal",
    xScale,
    animatedPointYScale,
    svgWidth,
    svgHeight
  )
  $: drawPointLayer(
    timeSeriesCanvas,
    timeSeriesPointRows,
    overallPredictionColumn,
    "orange",
    xScale,
    animatedPointYScale,
    svgWidth,
    svgHeight
  )
  $: drawPointLayer(
    comparativeCanvas,
    comparativePointRows,
    comparing ? predictionColumn(hoverYear) : null,
    "#00c07f",
    xScale,
    animatedPointYScale,
    svgWidth,
    svgHeight
  )

  let movingAverage = (rows, field, range) =>
    sma(
      rows.filter(v => v[field]).map(v => v[field]),
      range
    ).map(v => parseFloat(v))

  function drawPointLayer(canvas, rows, field, color, currentXScale, currentYScale, currentSvgWidth, currentSvgHeight) {
    if (!canvas || !field || !currentXScale || !currentYScale || !currentSvgWidth || !currentSvgHeight) return

    let pixelRatio = typeof window == "undefined" ? 1 : window.devicePixelRatio || 1
    let canvasWidth = Math.ceil(currentSvgWidth * pixelRatio)
    let canvasHeight = Math.ceil(currentSvgHeight * pixelRatio)

    if (canvas.width != canvasWidth || canvas.height != canvasHeight) {
      canvas.width = canvasWidth
      canvas.height = canvasHeight
    }

    let context = canvas.getContext("2d")
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
    context.clearRect(0, 0, currentSvgWidth, currentSvgHeight)
    context.fillStyle = color
    context.beginPath()

    rows.forEach(row => {
      let value = row[field]
      if (!value) return

      let x = plotMargin.left + currentXScale(row.parsedDate)
      let y = currentYScale(value)

      context.moveTo(x + 4, y)
      context.arc(x, y, 4, 0, Math.PI * 2)
    })

    context.fill()
  }

  function nearestObservation(pointerX, pointerY) {
    if (!observationPointsVisible || !observationPointRows.length || !animatedPointYScale || !xScale) return null

    let targetDate = xScale.invert(pointerX)
    let pointIndex = d3.bisector(d => d.parsedDate).left(observationPointRows, targetDate)
    let candidates = [observationPointRows[pointIndex - 1], observationPointRows[pointIndex]].filter(Boolean)
    let nearest = candidates.reduce((closest, row) => {
      let distance = Math.hypot(xScale(row.parsedDate) - pointerX, animatedPointYScale(row.observed_victims) - pointerY)

      return !closest || distance < closest.distance ? { row, distance } : closest
    }, null)

    return nearest?.distance <= 8 ? nearest.row : null
  }

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
      input: year == latestObservedYear ? `${minYear}–Present` : year == minYear ? `${minYear}` : `${minYear}–${year}`,
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

  function handleHover(e) {
    let [pointerX, pointerY] = d3.pointer(e, plotGroup)
    let year = xScale.invert(pointerX).getFullYear()

    if (year != hoverYear) {
      hoverYear = year
    }

    hoveredObservation = nearestObservation(pointerX, pointerY)
  }

  $: comparing = hoverYear != null && hoverYear < latestObservedYear
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
      ? `Model Input: What years of data were used to generate these predictions?\nTotal Victims: How many total victims does the model think there will be in the next ${forecastDayCount} days?\nAvg Victims per Day: How many victims does the model think there will be daily for the next ${forecastDayCount} days?\nAvg Yearly Trend: What is the average change between these predictions annually?`
      : `Model Input: What years of data were used to generate these predictions?\nTotal Victims: How many total victims does the model think there have been since ${firstDate}?\nAvg Victims per Day: How many victims does the model think there have been daily since ${firstDate}?\nAvg Yearly Trend: What is the average change between these predictions annually?\nRMSE: How do these predictions compare to the actual number of victims recorded daily since ${firstDate}?`,
    hoveredObservation: hoveredObservation
      ? `Date: ${format(hoveredObservation.parsedDate, "yyyy-MM-dd")}\nVictims: ${hoveredObservation.observed_victims.toLocaleString()}`
      : "",
  }

  $: {
    if (comparing && sliders.timeSeries && filteredData && xScale && yScale) {
      let movingAverages = movingAverage(
        filteredData,
        predictionColumn(hoverYear),
        sliderItems[sliders.timeSeries].label
      )

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

<div
  class="flex flex-col w-full h-screen justify-center items-center mb-10"
  bind:clientWidth={width}
  bind:clientHeight={height}
>
  <div class="lg:hidden px-8 text-center text-lg">This visualization is best viewed on a larger screen.</div>
  <div class="hidden lg:block">
    {#if filteredData}
      <div class="flex flex-col self-start mt-4 mb-3 text-sm">
        <div class="flex items-center gap-1.5">
          <CheckboxFilter
            labelClasses="font-medium"
            label="Scale to Include the Las Vegas Shooting"
            value={checkboxFilters.lasVegasScale}
            selection={checkboxFilters.lasVegasScale ? [true] : []}
            deselection={checkboxFilters.lasVegasScale ? [] : [true]}
            on:update={({ detail: e }) => (checkboxFilters.lasVegasScale = !e.value)}
          />
          <InfoTooltip title={tooltipText.lasVegasScale} />
        </div>
        <CheckboxFilter
          labelClasses="font-medium"
          label="Display Daily Observations"
          value={checkboxFilters.displayObservations}
          selection={checkboxFilters.displayObservations ? [true] : []}
          deselection={checkboxFilters.displayObservations ? [] : [true]}
          on:update={({ detail: e }) => (checkboxFilters.displayObservations = !e.value)}
        />
        <CheckboxFilter
          labelClasses="font-medium"
          label="Display Time Series Models"
          value={checkboxFilters.displayModels}
          selection={checkboxFilters.displayModels ? [true] : []}
          deselection={checkboxFilters.displayModels ? [] : [true]}
          on:update={({ detail: e }) => (checkboxFilters.displayModels = !e.value)}
        />
        <span class="flex flex-col items-center text-sm" class:italic={comparing}>
          {comparing ? "Comparing Historical Forecasts..." : "Hover to Compare Historical Forecasts"}
        </span>
      </div>
      {#if svgWidth && svgHeight}
        <div
          class="overflow-scroll w-full border-solid border-black"
          width={chartViewportWidth}
          style="max-width:{chartViewportWidth}px"
        >
          <div class="relative" style="width:{svgWidth}px; height:{svgHeight}px">
            <canvas
              bind:this={observationsCanvas}
              class="pointer-events-none absolute left-0 top-0 {fadeClasses}"
              aria-hidden="true"
              style="width:{svgWidth}px; height:{svgHeight}px; opacity:{observationPointsVisible ? 1 : 0}"
            />
            <canvas
              bind:this={timeSeriesCanvas}
              class="pointer-events-none absolute left-0 top-0 {fadeClasses}"
              aria-hidden="true"
              style="width:{svgWidth}px; height:{svgHeight}px; opacity:{timeSeriesPointsVisible ? 1 : 0}"
            />
            <canvas
              bind:this={comparativeCanvas}
              class="pointer-events-none absolute left-0 top-0 {fadeClasses}"
              aria-hidden="true"
              style="width:{svgWidth}px; height:{svgHeight}px; opacity:{comparativePointsVisible ? 0.9 : 0}"
            />
            <svg
              class="absolute left-0 top-0 flex flex-col justify-center items-center overflow-x-scroll"
              width={svgWidth}
              height={svgHeight}
              id="graph"
            >
              <g
                bind:this={plotGroup}
                transform="translate({plotMargin.left}, {0})"
                role="presentation"
                on:mousemove={handleHover}
                on:mouseleave={() => {
                  hoverYear = null
                  hoveredObservation = null
                }}
              >
                <rect
                  x={0}
                  y={plotMargin.top}
                  width={xAxisWidth}
                  height={yScale(0) - plotMargin.top}
                  fill="transparent"
                />
                {#if comparing}
                  <rect
                    class="non-reactive"
                    x={0}
                    y={plotMargin.top}
                    width={Math.min(xScale(parseLocalDate(`${hoverYear + 1}-01-01`)), xAxisWidth)}
                    height={yScale(0) - plotMargin.top}
                    fill="black"
                    fill-opacity={0.04}
                    stroke="black"
                    stroke-width={1}
                  />
                {/if}
                <rect
                  class="non-reactive"
                  x={xScale(parseLocalDate(forecastStartDate))}
                  y={plotMargin.top}
                  width={xAxisWidth - xScale(parseLocalDate(forecastStartDate))}
                  height={yScale(0) - plotMargin.top}
                  fill="black"
                  opacity={0.06}
                />
                <line
                  class="non-reactive"
                  stroke="black"
                  stroke-dasharray="4 4"
                  x1={xScale(parseLocalDate(forecastStartDate))}
                  x2={xScale(parseLocalDate(forecastStartDate))}
                  y1={plotMargin.top}
                  y2={yScale(0)}
                />
                <text
                  class="non-reactive fill-chart-1 text-sm italic"
                  x={(xScale(parseLocalDate(forecastStartDate)) + xAxisWidth) / 2}
                  y={plotMargin.top + 14}
                  text-anchor="middle"
                >
                  Next {forecastDayCount.toLocaleString()} days...
                </text>
                <path
                  class={observationPathVisible
                    ? `${fadeClasses} hover:stroke-4 hover:stroke-teal`
                    : `${fadeClasses} non-reactive`}
                  fill="transparent"
                  stroke="teal"
                  stroke-width={3}
                  style="opacity:{observationPathVisible ? 1 : 0}"
                  d={$animatedPaths.observations}
                />
                {#if hoveredObservation && observationPointsVisible && animatedPointYScale}
                  <circle
                    class="hover:cursor-help"
                    fill="teal"
                    stroke="black"
                    r={5}
                    cx={xScale(hoveredObservation.parsedDate)}
                    cy={animatedPointYScale(hoveredObservation.observed_victims)}
                    title={tooltipText.hoveredObservation}
                    use:tooltip
                  />
                {/if}
                <path
                  class={timeSeriesPathVisible
                    ? `${fadeClasses} hover:stroke-4 hover:stroke-orange`
                    : `${fadeClasses} non-reactive`}
                  fill="transparent"
                  stroke="orange"
                  stroke-width={3}
                  style="opacity:{timeSeriesPathVisible ? 1 : 0}"
                  d={$animatedPaths.timeSeries}
                />
                {#if comparing && checkboxFilters.displayModels}
                  <path
                    class="non-reactive {fadeClasses}"
                    fill="transparent"
                    stroke="#00c07f"
                    stroke-width={3}
                    style="opacity:{comparativePathVisible ? 0.9 : 0}"
                    d={comparativePath}
                  />
                {/if}
              </g>
              <g class="non-reactive text-sm" transform="translate({plotMargin.left}, {0})">
                <path class="stroke-chart-1" fill="transparent" opacity={0.7} d="M0,{plotMargin.top}V{yScale(0)}" />
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
                transform="translate(16, {(plotMargin.top + yScale(0)) / 2}) rotate(-90)"
              >
                Total Victims
              </text>
              <InfoIcon title={tooltipText.yAxis} cx={12} cy={(plotMargin.top + yScale(0)) / 2 - 78} />
              <text
                class="non-reactive fill-chart-1 text-lg"
                text-anchor="middle"
                x={plotMargin.left + xAxisWidth / 2}
                y={svgHeight - 14}
              >
                Date
              </text>
              <InfoIcon title={tooltipText.xAxis} cx={plotMargin.left + xAxisWidth / 2 + 32} cy={svgHeight - 20} />
              <g class="non-reactive text-sm" transform="translate({plotMargin.left + 8}, {plotMargin.top + 8})">
                {#each legendItems as item, i (item.label)}
                  <g transform="translate(0, {i * 16})">
                    {#if !item.visible}
                      <text class="fill-chart-1" x={8} dy="0.32em" text-anchor="middle">∅</text>
                    {:else if item.aggregated}
                      <line stroke={item.color} stroke-width={3.5} x1={0} x2={16} y1={0} y2={0} />
                    {:else}
                      <circle fill={item.color} cx={8} cy={0} r={4} />
                    {/if}
                    <text class="fill-chart-1" x={24} dy="0.32em">{item.label}</text>
                  </g>
                {/each}
              </g>
              <g class="non-reactive text-sm" transform="translate({plotMargin.left}, {yScale(0)})">
                <path class="stroke-chart-1" fill="transparent" opacity={0.7} d="M0,0V0H{xAxisWidth}V0" />
                {#each xScale.ticks() as xTick (xTick)}
                  <g transform="translate({xScale(xTick)}, {0})">
                    <line class="stroke-chart-1" opacity={0.7} y1={0.5} y2={xTickHeight} />
                    <Text
                      classes="text-center"
                      overflowBody={false}
                      wrapBody={false}
                      x={-xTickLength / 2}
                      width={Math.min(xTickLength, xAxisWidth - xScale(xTick) + xTickLength / 2)}
                      height={xAxisHeight}
                      bodyPadding={{ top: xTickHeight + xTickVerticalOffset, right: 0, bottom: 0, left: 0 }}
                      bodyText={xAxisWidth - xScale(xTick) >= getTextWidth(String(xTick.getFullYear()), xTickLabelSize)
                        ? String(xTick.getFullYear())
                        : ""}
                    />
                  </g>
                {/each}
              </g>
            </svg>
          </div>
        </div>
      {/if}
      <div class="flex items-start gap-6 w-full mt-5 text-sm" style="max-width:{chartViewportWidth}px">
        <div>
          <div class="mb-2 flex items-center gap-1.5 font-medium">
            Prediction Timeframe
            <InfoTooltip title={tooltipText.timeframe} />
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
        <table class="border-collapse">
          <thead>
            <tr>
              <th class="pb-1 text-left align-bottom [border-bottom-style:solid] border-b-[3.5px] border-b-chart-1">
                <div class="flex items-center gap-1.5 font-medium">
                  Metrics
                  <InfoTooltip title={tooltipText.metrics} />
                </div>
              </th>
              <th
                class="px-3 pb-1 font-medium !text-right align-bottom [border-bottom-style:solid] border-b-[3.5px] border-b-[orange]"
                >Overall Model</th
              >
              <th
                class="px-3 pb-1 font-medium !text-right align-bottom [border-bottom-style:solid] border-b-[3.5px] border-b-[#00c07f]"
                >Comparative Model</th
              >
            </tr>
          </thead>
          <tbody>
            {#each metricRows as row (row.key)}
              <tr>
                <td class="pr-3 whitespace-nowrap"
                  >{row.label}{#if row.rounded}&nbsp;<em>(Rounded)</em>{/if}</td
                >
                <td class="px-3 text-right">{overallMetrics ? overallMetrics[row.key] : ""}</td>
                <td class="px-3 text-right">{comparativeMetrics ? comparativeMetrics[row.key] : "—"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
        <div class="grow grid grid-cols-2 gap-6 mt-4">
          <div>
            <div class="flex justify-center items-center gap-1.5 font-medium">
              Moving Average for<br />Daily Observations
              <InfoTooltip title={tooltipText.observationsSlider} />
            </div>
            <Slider
              wrapperClasses="w-full"
              items={sliderItems}
              value={sliders.observations}
              step={1}
              min={0}
              max={sliderItems.length - 1}
              float={true}
              labels={true}
              middle={true}
              on:valueChange={({ detail: e }) => (sliders.observations = e.d)}
            />
          </div>
          <div>
            <div class="flex justify-center items-center gap-1.5 font-medium">
              Moving Average for<br />Time Series Models
              <InfoTooltip title={tooltipText.timeSeriesSlider} />
            </div>
            <Slider
              wrapperClasses="w-full"
              items={sliderItems}
              value={sliders.timeSeries}
              step={1}
              min={0}
              max={sliderItems.length - 1}
              float={true}
              labels={true}
              middle={true}
              on:valueChange={({ detail: e }) => (sliders.timeSeries = sliderItems[e.d].value)}
            />
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

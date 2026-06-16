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
  let predictionColumnName = year => `predicted_victims_${year}`
  let minYear = Math.min(...data.map(yearFromDate))
  let latestObservedYear = Math.max(...data.filter(d => !d.is_forecast).map(yearFromDate))
  let overallPredictionColumnName = predictionColumnName(latestObservedYear)
  let overallPredictionMovingAverageColumnName = `${overallPredictionColumnName}_moving_average`

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
  let graphWidth

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
      duration: 600,
      delay: 100,
      easing: cubicInOut,
    }
  )

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
          .slice(chartOptions.lasVegasScale ? 0 : 1)
          .sort((a, b) => a.date.localeCompare(b.date))

        let getMovingAverage = function (field, range) {
          return sma(
            filteredData.filter(v => v[field]).map(v => v[field]),
            range
          ).map(v => parseFloat(v))
        }

        let observationsMovingAverage = getMovingAverage(
          "observed_victims",
          movingAverageOptions[movingAverageSelections.observations].label
        )
        let timeSeries = getMovingAverage(
          overallPredictionColumnName,
          movingAverageOptions[movingAverageSelections.timeSeries].label
        )

        // TODO: fix process so it is not based on an iterator, otherwise it will be wrong when items (last vegas) are filtered out.
        filteredData.forEach((d, i) => {
          d.observed_victims_moving_average = observationsMovingAverage[i]
          d[overallPredictionMovingAverageColumnName] = timeSeries[i]
        })

        xScale = d3.scaleTime(
          d3.extent(filteredData, d => parseLocalDate(d.date)),
          [0, xAxisWidth]
        )

        xTickLength = xScale(xScale.ticks()[1]) - xScale(xScale.ticks()[0])

        yScale = d3.scaleLinear(
          [
            0,
            d3.max(filteredData, d =>
              movingAverageSelections.observations && movingAverageSelections.timeSeries
                ? Math.max(d.observed_victims_moving_average, d[overallPredictionMovingAverageColumnName])
                : movingAverageSelections.observations
                  ? Math.max(d.observed_victims_moving_average, d[overallPredictionColumnName])
                  : movingAverageSelections.timeSeries
                    ? Math.max(d.observed_victims, d[overallPredictionMovingAverageColumnName])
                    : Math.max(d.observed_victims, d[overallPredictionColumnName])
            ),
          ],
          [svgHeight - xAxisHeight, plotMargin.top]
        )

        pathGeneratorFor = function (field) {
          return d3
            .line()
            .curve(d3.curveNatural)
            .x(d => xScale(parseLocalDate(d.date)))
            .y(d => yScale(d[field]))
        }
      }

      animatedPaths.set({
        observations: movingAverageSelections.observations
          ? pathGeneratorFor("observed_victims_moving_average")(
              filteredData.filter(v => v.observed_victims_moving_average)
            )
          : pathGeneratorFor("observed_victims")(filteredData.filter(v => v.observed_victims)),
        timeSeries: movingAverageSelections.timeSeries
          ? pathGeneratorFor(overallPredictionMovingAverageColumnName)(
              filteredData.filter(v => v[overallPredictionMovingAverageColumnName])
            )
          : pathGeneratorFor(overallPredictionColumnName)(filteredData.filter(v => v.observed_victims)),
      })
    }
  }

  let timeframeOptions = [
    { value: "Past - Present", label: `${minYear} - Present` },
    { value: "Next 365 Days", label: "Next 365 Days" },
  ]

  let selectedTimeframe = timeframeOptions[0]

  let movingAverageOptions = [
    { value: 0, label: 0 },
    { value: 1, label: 5 },
    { value: 2, label: 10 },
    { value: 3, label: 15 },
    { value: 4, label: 20 },
    { value: 5, label: 25 },
    { value: 6, label: 30 },
  ]

  let chartOptions = {
    lasVegasScale: true,
    displayObservations: true,
    displayModels: true,
  }

  let movingAverageSelections = { observations: 0, timeSeries: 2 }

  let forecastDayCount = data.filter(d => d.is_forecast).length
  let forecastStartDate = data.find(d => d.is_forecast).date

  let firstDate = format(parseLocalDate(data[0].date), "M/d/yy")

  let hoverYear = null

  $: legendItems = [
    {
      label: "Daily Observations",
      color: "teal",
      visible: chartOptions.displayObservations,
      aggregated: movingAverageSelections.observations > 0,
    },
    {
      label: "Overall Model",
      color: "orange",
      visible: chartOptions.displayModels,
      aggregated: movingAverageSelections.timeSeries > 0,
    },
    {
      label: "Comparative Model",
      color: "#00c07f",
      visible: chartOptions.displayModels && hoverYear != null && hoverYear < latestObservedYear,
      aggregated: movingAverageSelections.timeSeries > 0,
    },
  ]

  let numObservations = data.filter(d => !d.is_forecast).length

  let plotGroup
  let comparativePath = null

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
    let predictionColumn = predictionColumnName(year)
    let rows = data.map((d, i) => ({ d, i })).filter(({ d }) => (isFutureTimeframe ? d.is_forecast : !d.is_forecast))

    let predSum = rows.reduce((sum, { d }) => sum + (d[predictionColumn] || 0), 0)
    let yearlyTrends = rows.map(({ i }) => yearlyTrendAt(i, predictionColumn)).filter(v => v != null)
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
          rows.reduce((sum, { d }) => sum + ((d[predictionColumn] || 0) - d.observed_victims) ** 2, 0) / numObservations
        )
      ).toLocaleString()
    }

    return result
  }

  function handleHover(e) {
    let year = xScale.invert(d3.pointer(e, plotGroup)[0]).getFullYear()

    if (year != hoverYear) {
      hoverYear = year
    }
  }

  $: comparing = hoverYear != null && hoverYear < latestObservedYear
  $: isFuture = selectedTimeframe.value == "Next 365 Days"

  $: overallMetrics = filteredData ? modelMetrics(latestObservedYear, isFuture) : null
  $: comparativeMetrics = comparing ? modelMetrics(hoverYear, isFuture) : null

  $: metricRows = [
    { label: "Model Input", key: "input" },
    { label: "Total Victims", key: "total" },
    { label: "Avg Victims per Day", key: "perDay" },
    { label: "Avg Yearly Trend", key: "trend", rounded: true },
    ...(isFuture ? [] : [{ label: "RMSE", key: "rmse", rounded: true }]),
  ]

  let lasVegasTooltip =
    "The Las Vegas shooting is the deadliest mass shooting in US history. With 548 total victims killed/injured, it is a major outlier in this dataset. Filter to see how this observation affects the scaling of the entire graph."
  let xAxisTooltip = "Individual incidents are summed together and grouped by date."
  let yAxisTooltip =
    "Includes all victims reported as injured or killed. Victims with unreported health statuses are not included."
  let observationsSliderTooltip =
    "Adjust the slider to specify a moving average for displaying daily observations. Units are in days, with 0 days displaying the actual/recorded observation."
  let timeSeriesSliderTooltip =
    "Adjust the slider to specify a moving average for displaying time series models. Units are in days, with 0 days displaying the exact prediction on a given day."

  const timeframeTooltip = `Use dropdown to compare time series model predictions for dates that took place in the past, or, take place in the next year (${forecastDayCount} days).`

  $: metricsTooltip = isFuture
    ? `Model Input: What years of data were used to generate these predictions?\nTotal Victims: How many total victims does the model think there will be in the next ${forecastDayCount} days?\nAvg Victims per Day: How many victims does the model think there will be daily for the next ${forecastDayCount} days?\nAvg Yearly Trend: What is the average change between these predictions annually?`
    : `Model Input: What years of data were used to generate these predictions?\nTotal Victims: How many total victims does the model think there have been since ${firstDate}?\nAvg Victims per Day: How many victims does the model think there have been daily since ${firstDate}?\nAvg Yearly Trend: What is the average change between these predictions annually?\nRMSE: How do these predictions compare to the actual number of victims recorded daily since ${firstDate}?`

  $: {
    if (comparing && movingAverageSelections.timeSeries && filteredData && xScale && yScale) {
      let movingAverages = movingAverage(
        filteredData,
        predictionColumnName(hoverYear),
        movingAverageOptions[movingAverageSelections.timeSeries].label
      )

      comparativePath = d3
        .line()
        .curve(d3.curveNatural)
        .x(d => xScale(parseLocalDate(d.date)))
        .y(d => yScale(d.value))(
        filteredData
          .map((d, i) => ({ date: d.date, value: movingAverages[i] }))
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
            value={chartOptions.lasVegasScale}
            selection={chartOptions.lasVegasScale ? [true] : []}
            deselection={chartOptions.lasVegasScale ? [] : [true]}
            on:update={({ detail: e }) => (chartOptions.lasVegasScale = !e.value)}
          />
          <InfoTooltip title={lasVegasTooltip} />
        </div>
        <CheckboxFilter
          labelClasses="font-medium"
          label="Display Daily Observations"
          value={chartOptions.displayObservations}
          selection={chartOptions.displayObservations ? [true] : []}
          deselection={chartOptions.displayObservations ? [] : [true]}
          on:update={({ detail: e }) => (chartOptions.displayObservations = !e.value)}
        />
        <CheckboxFilter
          labelClasses="font-medium"
          label="Display Time Series Models"
          value={chartOptions.displayModels}
          selection={chartOptions.displayModels ? [true] : []}
          deselection={chartOptions.displayModels ? [] : [true]}
          on:update={({ detail: e }) => (chartOptions.displayModels = !e.value)}
        />
        <span class="flex flex-col items-center text-sm {comparing ? 'italic' : ''}">
          {comparing ? "Comparing Historical Forecasts..." : "Hover to Compare Historical Forecasts"}
        </span>
      </div>
      {#if svgWidth && svgHeight}
        <div
          class="overflow-scroll w-full border-solid border-black"
          width={chartViewportWidth}
          style="max-width:{chartViewportWidth}px"
        >
          <svg
            class="flex flex-col justify-center items-center overflow-x-scroll"
            width={svgWidth}
            height={svgHeight}
            id="graph"
          >
            <g
              bind:this={plotGroup}
              transform="translate({plotMargin.left}, {0})"
              role="presentation"
              on:mousemove={handleHover}
              on:mouseleave={() => (hoverYear = null)}
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
                class="non-reactive stroke-black"
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
              {#if movingAverageSelections.observations <= 1}
                {#each filteredData as d (d.date)}
                  {#if d.observed_victims}
                    <circle
                      class={!chartOptions.displayObservations || movingAverageSelections.observations
                        ? "non-reactive"
                        : "stroke stroke-teal hover:stroke-2 hover:stroke-black hover:cursor-help"}
                      fill={!chartOptions.displayObservations || movingAverageSelections.observations
                        ? "transparent"
                        : "teal"}
                      r={4}
                      cx={xScale(parseLocalDate(d.date))}
                      cy={yScale(d.observed_victims)}
                      title={"Date: " +
                        format(parseLocalDate(d.date), "yyyy-MM-dd") +
                        "\nVictims: " +
                        d.observed_victims.toLocaleString()}
                      use:tooltip
                    />
                  {/if}
                {/each}
              {/if}
              <path
                class={chartOptions.displayObservations && movingAverageSelections.observations
                  ? "hover:stroke-4 hover:stroke-teal"
                  : "non-reactive"}
                fill="transparent"
                stroke={chartOptions.displayObservations && movingAverageSelections.observations
                  ? "teal"
                  : "transparent"}
                stroke-width={3}
                d={$animatedPaths.observations}
              />
              {#if movingAverageSelections.timeSeries <= 1}
                {#each filteredData as d (d.date)}
                  {#if d[overallPredictionColumnName]}
                    <circle
                      class={!chartOptions.displayModels || movingAverageSelections.timeSeries
                        ? "non-reactive"
                        : "stroke stroke-orange hover:stroke-2 hover:stroke-black hover:cursor-help"}
                      fill={!chartOptions.displayModels || movingAverageSelections.timeSeries
                        ? "transparent"
                        : "orange"}
                      r={4}
                      cx={xScale(parseLocalDate(d.date))}
                      cy={yScale(d[overallPredictionColumnName])}
                    />
                  {/if}
                {/each}
              {/if}
              <path
                class={chartOptions.displayModels && movingAverageSelections.timeSeries
                  ? "hover:stroke-4 hover:stroke-orange"
                  : "non-reactive"}
                fill="transparent"
                stroke={chartOptions.displayModels && movingAverageSelections.timeSeries ? "orange" : "transparent"}
                stroke-width={3}
                d={$animatedPaths.timeSeries}
              />
              {#if comparing && chartOptions.displayModels && movingAverageSelections.timeSeries}
                <path
                  class="non-reactive"
                  fill="transparent"
                  stroke="#00c07f"
                  stroke-width={3}
                  opacity={0.9}
                  d={comparativePath}
                />
              {:else if comparing && chartOptions.displayModels}
                {#each filteredData as d (d.date)}
                  {#if d[predictionColumnName(hoverYear)]}
                    <circle
                      class="non-reactive"
                      fill="#00c07f"
                      r={4}
                      cx={xScale(parseLocalDate(d.date))}
                      cy={yScale(d[predictionColumnName(hoverYear)])}
                    />
                  {/if}
                {/each}
              {/if}
            </g>
            <g class="non-reactive text-sm" transform="translate({plotMargin.left}, {0})">
              <path class="fill-transparent stroke-chart-1 opacity-70" d="M0,{plotMargin.top}V{yScale(0)}" />
              {#each yScale.ticks() as yTick (yTick)}
                <g transform="translate(0, {yScale(yTick)})">
                  <line class="stroke-chart-1 opacity-70" x1={-xTickHeight} x2={0} />
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
            <InfoIcon title={yAxisTooltip} cx={12} cy={(plotMargin.top + yScale(0)) / 2 - 78} />
            <text
              class="non-reactive fill-chart-1 text-lg"
              text-anchor="middle"
              x={plotMargin.left + xAxisWidth / 2}
              y={svgHeight - 14}
            >
              Date
            </text>
            <InfoIcon title={xAxisTooltip} cx={plotMargin.left + xAxisWidth / 2 + 32} cy={svgHeight - 20} />
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
              <path class="fill-transparent stroke-chart-1 opacity-70" d="M0,0V0H{xAxisWidth}V0" />
              {#each xScale.ticks() as xTick (xTick)}
                <g transform="translate({xScale(xTick)}, {0})">
                  <line class="stroke-chart-1 opacity-70" y1={0.5} y2={xTickHeight} />
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
      {/if}
      <div class="flex items-start gap-6 w-full mt-5 text-sm" style="max-width:{chartViewportWidth}px">
        <div>
          <div class="mb-2 flex items-center gap-1.5 font-medium">
            Prediction Timeframe
            <InfoTooltip title={timeframeTooltip} />
          </div>
          <div class="w-36">
            <Select
              items={timeframeOptions}
              value={selectedTimeframe}
              clearable={false}
              centeredValue={true}
              centeredItems={true}
              on:valueChange={({ detail: e }) => (selectedTimeframe = e.d)}
            />
          </div>
        </div>
        <table class="border-collapse">
          <thead>
            <tr>
              <th class="pb-1 text-left align-bottom [border-bottom-style:solid] border-b-[3.5px] border-b-chart-1">
                <div class="flex items-center gap-1.5 font-medium">
                  Metrics
                  <InfoTooltip title={metricsTooltip} />
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
              <InfoTooltip title={observationsSliderTooltip} />
            </div>
            <Slider
              wrapperClasses="w-full"
              items={movingAverageOptions}
              value={movingAverageSelections.observations}
              step={1}
              min={0}
              max={movingAverageOptions.length - 1}
              float={true}
              labels={true}
              middle={true}
              on:valueChange={({ detail: e }) => (movingAverageSelections.observations = e.d)}
            />
          </div>
          <div>
            <div class="flex justify-center items-center gap-1.5 font-medium">
              Moving Average for<br />Time Series Models
              <InfoTooltip title={timeSeriesSliderTooltip} />
            </div>
            <Slider
              wrapperClasses="w-full"
              items={movingAverageOptions}
              value={movingAverageSelections.timeSeries}
              step={1}
              min={0}
              max={movingAverageOptions.length - 1}
              float={true}
              labels={true}
              middle={true}
              on:valueChange={({ detail: e }) => (movingAverageSelections.timeSeries = movingAverageOptions[e.d].value)}
            />
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>
<svelte:head>
  <style>
    g.group {
      transition: d 600ms cubic-bezier(0.65, 0, 0.35, 1);
      transition-delay: 100ms;
      /* will-change: transform; */
    }

    /* .group circle {
      transition: cy 600ms cubic-bezier(0.65, 0, 0.35, 1);
      transition-delay: 100ms;
      will-change: transform, cy;
    } */
  </style>
</svelte:head>

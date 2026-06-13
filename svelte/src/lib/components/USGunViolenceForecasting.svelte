<script>
  import * as d3 from "d3"
  import { interpolateString } from "d3-interpolate"
  import { format, parseISO } from "date-fns"
  import sma from "sma"
  import { tweened } from "svelte/motion"
  import { cubicInOut } from "svelte/easing"
  import { CheckboxFilter, InfoIcon, InfoTooltip, Select, Slider, Text } from "svelte-lib/components"
  import { filterUnique, getCSSCustomProperty, getTextWidth, tooltip } from "svelte-lib/functions"
  import data from "../static/data.json"

  let width
  let height
  let svgWidth
  let visibleSVGWidth
  let svgHeight
  let graphStrokeWidth = 1

  let xScale
  let yScale
  let xTickLength
  let xAxisWidth
  // margins around the plot, matching the proportions of the original d3 project.
  let graphPadding = { top: 20, right: 20, bottom: 65, left: 65 }
  // the height of the x axis ticks.
  let xTickHeight = 10
  // the vertical distance between each xTick and xTick label.
  let xTickVerticalOffset = 8.5
  // the font size for the x tick labels.
  let xTickLabelSize = 12

  // the full bottom band holding the x axis ticks, year labels, and "Date" title.
  let xAxisHeight = graphPadding.bottom

  let filteredData

  let line

  let pxPerD = 0.4
  let graphWidth
  let visibleXAxisWidth

  // TODO: combine paths into one variable.
  let observationsPath = tweened(null, {
    interpolate: interpolateString,
    duration: 600,
    delay: 100,
    cubicInOut,
  })

  let timeSeriesPath = tweened(null, {
    interpolate: interpolateString,
    duration: 600,
    delay: 100,
    cubicInOut,
  })

  $: {
    if (width) {
      visibleSVGWidth = width * 0.8
      graphWidth = data.length * pxPerD
      svgHeight = height * 0.65
      svgWidth = graphWidth + graphPadding.left + graphPadding.right + graphStrokeWidth * 2
      xAxisWidth = svgWidth - graphPadding.right - graphPadding.left - graphStrokeWidth * 2
      visibleXAxisWidth = visibleSVGWidth - graphPadding.right - graphPadding.left - graphStrokeWidth * 2

      if (data.length) {
        filteredData = data.sort((a, b) => b.num_harmed - a.num_harmed).slice(checkboxFilters.lasVegasScale ? 0 : 1)
        filteredData = filteredData.sort((a, b) => new Date(a.date) - new Date(b.date))

        let getMovingAverage = function (field, range) {
          return sma(
            filteredData.filter(v => v[field]).map(v => v[field]),
            range
          ).map(v => parseFloat(v))
        }

        let observationsMovingAverage = getMovingAverage("num_harmed", sliderItems[sliders.observations].label)
        let timeSeries = getMovingAverage("pred_2019", sliderItems[sliders.timeSeries].label)

        // TODO: fix process so it is not based on an iterator, otherwise it will be wrong when items (last vegas) are filtered out.
        filteredData.forEach((d, i) => {
          d.num_harmed_moving_average = observationsMovingAverage[i]
          d.pred_2019_moving_average = timeSeries[i]
        })

        xScale = d3.scaleTime(
          d3.extent(filteredData, d => new Date(d.date)),
          [0, xAxisWidth]
        )

        xTickLength = xScale(xScale.ticks()[1]) - xScale(xScale.ticks()[0])

        yScale = d3.scaleLinear(
          [
            0,
            d3.max(filteredData, d =>
              sliders.observations && sliders.timeSeries
                ? Math.max(d.num_harmed_moving_average, d.pred_2019_moving_average)
                : sliders.observations
                  ? Math.max(d.num_harmed_moving_average, d.pred_2019)
                  : sliders.timeSeries
                    ? Math.max(d.num_harmed, d.pred_2019_moving_average)
                    : Math.max(d.num_harmed, d.pred_2019)
            ),
          ],
          [svgHeight - xAxisHeight, graphPadding.top]
        )

        line = function (field) {
          return d3
            .line()
            .curve(d3.curveNatural)
            .x(d => xScale(new Date(d.date)))
            .y(d => yScale(d[field]))
        }
      }

      observationsPath.set(
        // line("num_harmed")(filteredData.filter(v => v.num_harmed))
        sliders.observations
          ? line("num_harmed_moving_average")(filteredData.filter(v => v.num_harmed_moving_average))
          : line("num_harmed")(filteredData.filter(v => v.num_harmed))
      )

      timeSeriesPath.set(
        line("pred_2019_moving_average")(filteredData.filter(v => v.pred_2019_moving_average))
        // sliders.timeSeries
        //   ? line("pred_2019_moving_average")(filteredData.filter(v => v.pred_2019_moving_average))
        //   : line("pred_2019")(filteredData.filter(v => v.num_harmed))
      )
    }
  }

  let minYear = Math.min(...data.map(d => d.year))

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

  let maxYearObserved = Math.max(...data.filter(d => d.non_observation != 1).map(d => d.year))
  let numFuturePredDays = data.filter(d => d.non_observation == 1).length
  let firstFutureDate = data.find(d => d.non_observation == 1).date

  let firstDate = format(
    data.reduce((min, d) => (d.date < min ? d.date : min), data[0].date),
    "M/d/yy"
  )

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
      visible: checkboxFilters.displayModels && hoverYear != null && hoverYear < maxYearObserved,
      aggregated: sliders.timeSeries > 0,
    },
  ]

  let numObservations = data.filter(d => d.non_observation != 1).length

  let plotGroup
  let comparativePath = null

  let movingAverage = (rows, field, range) =>
    sma(
      rows.filter(v => v[field]).map(v => v[field]),
      range
    ).map(v => parseFloat(v))

  function metrics(year, future) {
    let predCol = `pred_${year}`
    let trendCol = `yearly_trend_calc_${year}`
    let rows = data.filter(d => (future ? d.non_observation == 1 : d.non_observation != 1))

    let predSum = rows.reduce((sum, d) => sum + (d[predCol] || 0), 0)
    let trendSum = rows.reduce((sum, d) => sum + (d[trendCol] || 0), 0)

    let result = {
      input: year == maxYearObserved ? `${minYear}–Present` : year == minYear ? `${minYear}` : `${minYear}–${year}`,
      total: Math.round(predSum).toLocaleString(),
      perDay: Math.round(predSum / rows.length).toLocaleString(),
      trend: Math.round(trendSum / (future ? numFuturePredDays : numObservations - numFuturePredDays)).toLocaleString(),
    }

    if (!future) {
      result.rmse = Math.round(
        Math.sqrt(rows.reduce((sum, d) => sum + ((d[predCol] || 0) - d.num_harmed) ** 2, 0) / numObservations)
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

  $: comparing = hoverYear != null && hoverYear < maxYearObserved
  $: isFuture = selectValue.value == "Next 365 Days"

  $: overallMetrics = filteredData ? metrics(maxYearObserved, isFuture) : null
  $: comparativeMetrics = comparing ? metrics(hoverYear, isFuture) : null

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

  $: timeframeTooltip = `Use dropdown to compare time series model predictions for dates that took place in the past, or, take place in the next year (${numFuturePredDays} days).`

  $: metricsTooltip = isFuture
    ? `Model Input: What years of data were used to generate these predictions?\nTotal Victims: How many total victims does the model think there will be in the next ${numFuturePredDays} days?\nAvg Victims per Day: How many victims does the model think there will be daily for the next ${numFuturePredDays} days?\nAvg Yearly Trend: What is the average change between these predictions annually?`
    : `Model Input: What years of data were used to generate these predictions?\nTotal Victims: How many total victims does the model think there have been since ${firstDate}?\nAvg Victims per Day: How many victims does the model think there have been daily since ${firstDate}?\nAvg Yearly Trend: What is the average change between these predictions annually?\nRMSE: How do these predictions compare to the actual number of victims recorded daily since ${firstDate}?`

  $: {
    if (comparing && sliders.timeSeries && filteredData && xScale && yScale) {
      let movingAverages = movingAverage(filteredData, `pred_${hoverYear}`, sliderItems[sliders.timeSeries].label)

      comparativePath = d3
        .line()
        .curve(d3.curveNatural)
        .x(d => xScale(new Date(d.date)))
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

<div class="flex flex-col w-full h-screen items-center" bind:clientWidth={width} bind:clientHeight={height}>
  <div class="flex flex-col w-full h-full justify-center items-center mb-10">
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
            <InfoTooltip title={lasVegasTooltip} />
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
          <span class="flex flex-col items-center text-sm {comparing ? 'italic' : ''}">
            {comparing ? "Comparing Historical Forecasts..." : "Hover to Compare Historical Forecasts"}
          </span>
        </div>
        {#if svgWidth && svgHeight}
          <div
            class="overflow-scroll w-full border-solid border-black"
            width={visibleSVGWidth}
            style="max-width:{visibleSVGWidth}px"
          >
            <svg
              class="flex flex-col justify-center items-center overflow-x-scroll"
              width={svgWidth}
              height={svgHeight}
              id="graph"
            >
              <g
                bind:this={plotGroup}
                transform="translate({graphPadding.left}, {0})"
                on:mousemove={handleHover}
                on:mouseleave={() => (hoverYear = null)}
              >
                <rect
                  x={0}
                  y={graphPadding.top}
                  width={xAxisWidth}
                  height={yScale(0) - graphPadding.top}
                  fill="transparent"
                />
                {#if comparing}
                  <rect
                    class="non-reactive"
                    x={0}
                    y={graphPadding.top}
                    width={Math.min(xScale(new Date(`${hoverYear + 1}-01-01`)), xAxisWidth)}
                    height={yScale(0) - graphPadding.top}
                    fill="black"
                    fill-opacity={0.04}
                    stroke="black"
                    stroke-width={1}
                  />
                {/if}
                <rect
                  class="non-reactive"
                  x={xScale(new Date(firstFutureDate))}
                  y={graphPadding.top}
                  width={xAxisWidth - xScale(new Date(firstFutureDate))}
                  height={yScale(0) - graphPadding.top}
                  fill="black"
                  opacity={0.06}
                />
                <line
                  class="non-reactive stroke-black"
                  stroke-dasharray="4 4"
                  x1={xScale(new Date(firstFutureDate))}
                  x2={xScale(new Date(firstFutureDate))}
                  y1={graphPadding.top}
                  y2={yScale(0)}
                />
                <text
                  class="non-reactive fill-chart-1 text-sm italic"
                  x={(xScale(new Date(firstFutureDate)) + xAxisWidth) / 2}
                  y={graphPadding.top + 14}
                  text-anchor="middle"
                >
                  Next {numFuturePredDays.toLocaleString()} days...
                </text>
                {#if sliders.observations <= 1}
                  {#each filteredData as d}
                    {#if d.num_harmed}
                      <circle
                        class={!checkboxFilters.displayObservations || sliders.observations
                          ? "non-reactive"
                          : "stroke stroke-teal hover:stroke-2 hover:stroke-black hover:cursor-help"}
                        fill={!checkboxFilters.displayObservations || sliders.observations ? "transparent" : "teal"}
                        r={4}
                        cx={xScale(new Date(d.date))}
                        cy={yScale(d.num_harmed)}
                        title={"Date: " + format(d.date, "yyyy-MM-dd") + "\nVictims: " + d.num_harmed.toLocaleString()}
                        use:tooltip
                      />
                    {/if}
                  {/each}
                {/if}
                <path
                  class={checkboxFilters.displayObservations && sliders.observations
                    ? "hover:stroke-4 hover:stroke-teal"
                    : "non-reactive"}
                  fill="transparent"
                  stroke={checkboxFilters.displayObservations && sliders.observations ? "teal" : "transparent"}
                  stroke-width={3}
                  d={$observationsPath}
                />
                {#if sliders.timeSeries <= 1}
                  {#each filteredData as d}
                    {#if d.pred_2019}
                      <circle
                        class={!checkboxFilters.displayModels || sliders.timeSeries
                          ? "non-reactive"
                          : "stroke stroke-orange hover:stroke-2 hover:stroke-black hover:cursor-help"}
                        fill={!checkboxFilters.displayModels || sliders.timeSeries ? "transparent" : "orange"}
                        r={4}
                        cx={xScale(new Date(d.date))}
                        cy={yScale(d.pred_2019)}
                      />
                    {/if}
                  {/each}
                {/if}
                <path
                  class={checkboxFilters.displayModels && sliders.timeSeries
                    ? "hover:stroke-4 hover:stroke-orange"
                    : "non-reactive"}
                  fill="transparent"
                  stroke={checkboxFilters.displayModels && sliders.timeSeries ? "orange" : "transparent"}
                  stroke-width={3}
                  d={$timeSeriesPath}
                />
                {#if comparing && checkboxFilters.displayModels && sliders.timeSeries}
                  <path
                    class="non-reactive"
                    fill="transparent"
                    stroke="#00c07f"
                    stroke-width={3}
                    opacity={0.9}
                    d={comparativePath}
                  />
                {:else if comparing && checkboxFilters.displayModels}
                  {#each filteredData as d}
                    {#if d[`pred_${hoverYear}`]}
                      <circle
                        class="non-reactive"
                        fill="#00c07f"
                        r={4}
                        cx={xScale(new Date(d.date))}
                        cy={yScale(d[`pred_${hoverYear}`])}
                      />
                    {/if}
                  {/each}
                {/if}
              </g>
              <g class="non-reactive text-sm" transform="translate({graphPadding.left}, {0})">
                <path class="fill-transparent stroke-chart-1 opacity-70" d="M0,{graphPadding.top}V{yScale(0)}" />
                {#each yScale.ticks() as yTick}
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
                transform="translate(16, {(graphPadding.top + yScale(0)) / 2}) rotate(-90)"
              >
                Total Victims
              </text>
              <InfoIcon title={yAxisTooltip} cx={12} cy={(graphPadding.top + yScale(0)) / 2 - 78} />
              <text
                class="non-reactive fill-chart-1 text-lg"
                text-anchor="middle"
                x={graphPadding.left + xAxisWidth / 2}
                y={svgHeight - 14}
              >
                Date
              </text>
              <InfoIcon title={xAxisTooltip} cx={graphPadding.left + xAxisWidth / 2 + 32} cy={svgHeight - 20} />
              <g class="non-reactive text-sm" transform="translate({graphPadding.left + 8}, {graphPadding.top + 8})">
                {#each legendItems as item, i}
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
              <g class="non-reactive text-sm" transform="translate({graphPadding.left}, {yScale(0)})">
                <path class="fill-transparent stroke-chart-1 opacity-70" d="M0,0V0H{xAxisWidth}V0" />
                {#each xScale.ticks() as xTick}
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
        <div class="flex items-start gap-6 w-full mt-5 text-sm" style="max-width:{visibleSVGWidth}px">
          <div>
            <div class="mb-2 flex items-center gap-1.5 font-medium">
              Prediction Timeframe
              <InfoTooltip title={timeframeTooltip} />
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
              {#each metricRows as row}
                <tr>
                  <td class="pr-3 whitespace-nowrap"
                    >{row.label}{#if row.rounded}{" "}<em>(Rounded)</em>{/if}</td
                  >
                  <td class="px-3 text-right">{overallMetrics ? overallMetrics[row.key] : ""}</td>
                  <td class="px-3 text-right">{comparativeMetrics ? comparativeMetrics[row.key] : "—"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
          <div class="grow">
            <div class="grid grid-cols-2 gap-6 mt-4">
              <div>
                <div class="flex justify-center items-center gap-1.5 font-medium">
                  Moving Average for<br />Daily Observations
                  <InfoTooltip title={observationsSliderTooltip} />
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
                  <InfoTooltip title={timeSeriesSliderTooltip} />
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
        </div>
      {/if}
    </div>
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

<script>
  import * as d3 from "d3"
  import { interpolateString } from "d3-interpolate"
  import { format } from "date-fns"
  import sma from "sma"
  import { tweened } from "svelte/motion"
  import { cubicInOut } from "svelte/easing"
  import { CheckboxFilter, Select, Slider, Text } from "svelte-lib/components"
  import { filterUnique, getCSSCustomProperty, getTextWidth, tooltip } from "svelte-lib/functions"
  import data from "../static/data.json"

  console.log(data)

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
  // the vertical distance between the bottom border and the x axis labels.
  let graphPadding = { top: 50, right: 50, bottom: 17.5, left: 50 }
  // the height of the x axis ticks.
  let xTickHeight = 10
  // the vertical distance between each xTick and xTick label.
  let xTickVerticalOffset = 8.5
  // the font size for the x tick labels.
  let xTickLabelSize = 14

  let xAxisHeight = graphPadding.bottom + xTickVerticalOffset + xTickHeight + xTickLabelSize

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
      svgHeight = height * 0.65
      graphWidth = data.length * pxPerD
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

  let selectItems = [
    { value: "Past - Present", label: "Past - Present" },
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
</script>

<div class="flex flex-col w-full h-screen items-center" bind:clientWidth={width} bind:clientHeight={height}>
  <div class="flex flex-col w-full h-full justify-center items-center mb-10">
    <div>
      {#if filteredData}
        <div class="flex flex-col self-start mt-4 mb-3">
          <CheckboxFilter
            labelClasses="font-medium"
            label="Scale to Include the Las Vegas Shooting"
            value={checkboxFilters.lasVegasScale}
            selection={checkboxFilters.lasVegasScale ? [true] : []}
            deselection={checkboxFilters.lasVegasScale ? [] : [true]}
            on:update={({ detail: e }) => (checkboxFilters.lasVegasScale = !e.value)}
          />
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
          <span class="flex flex-col items-center text-lg">Hover to Compare Historical Forecasts</span>
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
              <g transform="translate({graphPadding.left}, {0})">
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
              </g>
              <g
                class="non-reactive text-sm"
                transform="translate({graphPadding.left}, {svgHeight - xAxisHeight - graphPadding.bottom})"
              >
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
        <div class="grid grid-cols-2" width={visibleSVGWidth}>
          <div class="mt-9">
            <div class="mb-2">Prediction Timeframe</div>
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
          <div>
            <span class="flex flex-col text-center text-xl font-medium mt-7">Moving Averages</span>
            <div class="grid grid-cols-2 mt-5">
              <Slider
                wrapperClasses="w-full"
                title="Daily Observations"
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
              <Slider
                wrapperClasses="w-full"
                title="Time Series Models"
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

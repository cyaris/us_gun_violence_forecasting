<script>
  import * as d3 from "d3"
  import { format } from "date-fns"
  import sma from "sma"
  import { CheckboxFilter, Select, Slider, Text } from "svelte-lib/components"
  import { filterUnique, getCSSCustomProperty, getTextWidth, tooltip } from "svelte-lib/functions"
  import data from "../static/data.json"

  console.log(data)

  // let data
  // fetch(
  //   "https://raw.githubusercontent.com/cyaris/us_gun_violence_forecasting/refs/heads/master/Web%20Interface/assets/csv/us_gun_violence_forecasting/us_harmed_victim_forecast_data.csv"
  // )
  //   .then(response => response.text())
  //   .then(csvText => {
  //     let rows = csvText.trim().split("\n")
  //     let columns = rows.shift().split(",")
  //     console.log("here: ", columns)

  //     data = rows.map(row => {
  //       let values = row.split(",")
  //       return columns.reduce((row, column, i) => {
  //         row[column] =
  //           column == "date"
  //             ? new Date(values[i])
  //             : ["num_harmed", "year"].includes(column)
  //               ? parseInt(values[i])
  //               : parseFloat(values[i])
  //         row.index = i
  //         return row
  //       }, {})
  //     })

  //     // console.log('data2', data2)
  //     console.log(data)
  //   })
  //   .catch(error => console.error("Error fetching CSV:", error))

  let width
  let height
  let svgWidth
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
  // minor margin adjustments for fitting elements within the svg.
  // let svgMargin = {
  //   top: 1,
  //   right: 1,
  //   bottom: 1,
  //   left: 0,
  // }

  let filteredData
  // let totalDays

  let line
  $: {
    if (width) {
      svgWidth = width * 0.8
      svgHeight = height * 0.65

      xAxisWidth = svgWidth - graphPadding.right - graphPadding.left - graphStrokeWidth * 2

      if (data.length) {
        filteredData = data.sort((a, b) => b.num_harmed - a.num_harmed).slice(checkboxFilters.lasVegasScale ? 0 : 1)
        filteredData = filteredData.sort((a, b) => new Date(a.date) - new Date(b.date))

        let getMovingAverage = function (field, range) {
          return sma(
            filteredData.filter(v => v[field]).map(v => v[field]),
            range
          ).map(v => parseFloat(v))
        }

        let observationsMovingAverage = getMovingAverage("num_harmed", sliders.dailyObservations * 5)
        let timeSeriesModels = getMovingAverage("pred_2019", sliders.timeSeriesModels * 5)
        // console.log("observationsMovingAverage: ", observationsMovingAverage)

        // TODO: fix process so it is not based on an iterator, otherwise it will be wrong when items (last vegas) are filtered out.
        filteredData.forEach((d, i) => {
          d.num_harmed_moving_average = observationsMovingAverage[i]
          d.pred_2019_moving_average = timeSeriesModels[i]
        })

        // totalDays =
        //   (Math.max(...filteredData.map(v => new Date(v.date).getTime())) -
        //     Math.min(...filteredData.map(v => new Date(v.date).getTime()))) /
        //   (1000 * 60 * 60 * 24)
        // console.log("total Days: " + totalDays)

        xScale = d3.scaleTime(
          d3.extent(filteredData, d => new Date(d.date)),
          [0, xAxisWidth]
        )

        xTickLength = xScale(xScale.ticks()[1]) - xScale(xScale.ticks()[0])
        // console.log("total xticks: " + xScale.ticks().length)

        yScale = d3.scaleLinear(
          [
            0,
            d3.max(filteredData, d =>
              sliders.dailyObservations && sliders.timeSeriesModels
                ? Math.max(d.num_harmed_moving_average, d.pred_2019_moving_average)
                : sliders.dailyObservations
                  ? Math.max(d.num_harmed_moving_average, d.pred_2019)
                  : sliders.timeSeriesModels
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
    }
  }

  let selectItems = [
    { value: "Past - Present", label: "Past - Present" },
    { value: "Next 365 Days", label: "Next 365 Days" },
  ]
  let selectValue = { value: "Past - Present", label: "Past - Present" }

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

  let sliders = { dailyObservations: 0, timeSeriesModels: 2 }
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
          <svg
            class="flex flex-col justify-center items-center overflow-hidden"
            width={svgWidth}
            height={svgHeight}
            id="graph"
          >
            <rect
              width={svgWidth - graphStrokeWidth * 2}
              height={svgHeight - graphStrokeWidth * 2}
              x={graphStrokeWidth}
              y={graphStrokeWidth}
              fill="transparent"
              stroke="black"
              stroke-width={graphStrokeWidth}
            ></rect>
            <g transform="translate({graphPadding.left}, {0})">
              {#if checkboxFilters.displayObservations}
                {#if sliders.dailyObservations}
                  <path
                    class="hover:stroke-4 hover:stroke-teal"
                    fill="transparent"
                    stroke="teal"
                    stroke-width={3}
                    d={line("num_harmed_moving_average")(filteredData.filter(v => v.num_harmed_moving_average))}
                  />
                {:else}
                  {#each filteredData as d}
                    {#if d.num_harmed}
                      <circle
                        class="stroke stroke-teal hover:stroke-2 hover:stroke-black hover:cursor-help"
                        fill="teal"
                        r={4}
                        cx={xScale(new Date(d.date))}
                        cy={yScale(d.num_harmed)}
                        title={"Date: " + format(d.date, "yyyy-MM-dd") + "\nVictims: " + d.num_harmed.toLocaleString()}
                        use:tooltip
                      />
                    {/if}
                  {/each}
                {/if}
              {/if}
              {#if checkboxFilters.displayModels}
                {#if sliders.timeSeriesModels}
                  <path
                    class="hover:stroke-4 hover:stroke-orange"
                    fill="transparent"
                    stroke="orange"
                    stroke-width={3}
                    d={line("pred_2019_moving_average")(filteredData.filter(v => v.pred_2019_moving_average))}
                  />
                {:else}
                  {#each filteredData as d}
                    {#if d.pred_2019}
                      <circle
                        class="stroke stroke-teal hover:stroke-2 hover:stroke-black hover:cursor-help"
                        fill="orange"
                        r={4}
                        cx={xScale(new Date(d.date))}
                        cy={yScale(d.pred_2019)}
                      />
                    {/if}
                  {/each}
                {/if}
              {/if}
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
          <div class="grid grid-cols-2" width={svgWidth}>
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
                  value={sliders.dailyObservations}
                  step={1}
                  min={0}
                  max={sliderItems.length - 1}
                  float={true}
                  labels={true}
                  middle={true}
                  on:valueChange={({ detail: e }) => (sliders.dailyObservations = e.d)}
                />
                <Slider
                  wrapperClasses="w-full"
                  title="Time Series Models"
                  items={sliderItems}
                  value={sliders.timeSeriesModels}
                  step={1}
                  min={0}
                  max={sliderItems.length - 1}
                  float={true}
                  labels={true}
                  middle={true}
                  on:valueChange={({ detail: e }) => (sliders.timeSeriesModels = sliderItems[e.d].value)}
                />
              </div>
            </div>
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>

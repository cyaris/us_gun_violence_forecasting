<script>
  import * as d3 from "d3"
  import { CheckboxFilter, Select, Slider, Text } from "svelte-lib/components"
  import { filterUnique, getCSSCustomProperty, getTextWidth, tooltip } from "svelte-lib/functions"
  import data from "../static/data.json"

  console.log(data)

  let width
  let height
  let svgWidth
  let svgHeight
  let graphStrokeSize = 1

  let xScale
  let xTickLength
  let xAxisWidth
  // the vertical distance between the bottom border and the x axis labels.
  let xAxisVerticalOffset = 10
  // the height of the x axis ticks.
  let xTickHeight = 10
  // the vertical distance between each xTick and xTick label.
  let xTickVerticalOffset = 8.5
  // the font size for the x tick labels.
  let xTickLabelSize = 14
  // minor margin adjustments for fitting elements within the svg.
  let svgMargin = {
    top: 1,
    right: 1,
    bottom: 1,
  }
  let xAxisMargin = 30
  let xAxisHeight = xAxisVerticalOffset + xTickVerticalOffset + xTickHeight + xTickLabelSize
  let totalDays
  $: {
    svgWidth = width * 0.65
    svgHeight = height * 0.65

    xAxisWidth = svgWidth - graphStrokeSize * 2 - xAxisMargin * 2

    totalDays =
      (Math.max(...data.map(v => new Date(v.date).getTime())) -
        Math.min(...data.map(v => new Date(v.date).getTime()))) /
      (1000 * 60 * 60 * 24)
    console.log("total Days:" + totalDays)

    xScale = d3.scaleTime(
      d3.extent(data, d => new Date(d.date)),
      [0, xAxisWidth]
    )

    xTickLength = xScale(xScale.ticks()[1]) - xScale(xScale.ticks()[0])

    console.log("total xticks: " + xScale.ticks().length)
  }

  // fetch(
  //   "https://raw.githubusercontent.com/cyaris/us_gun_violence_forecasting/refs/heads/master/Web%20Interface/assets/csv/us_gun_violence_forecasting/us_harmed_victim_forecast_data.csv"
  // )
  //   .then(response => response.text())
  //   .then(csvText => {
  //     let rows = csvText.trim().split("\n")
  //     let columns = rows.shift().split(",")

  //     data = rows.map(row => {
  //       let values = row.split(",")
  //       return columns.reduce((row, column, i) => {
  //         row[column] =
  //           column == "date"
  //             ? Date(values[i])
  //             : ["num_harmed", "year"].includes(column)
  //               ? parseInt(values[i])
  //               : parseFloat(values[i])
  //         row.index = i
  //         return row
  //       }, {})
  //     })

  //     console.log(data)
  //   })
  //   .catch(error => console.error("Error fetching CSV:", error))

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
</script>

<div class="flex flex-col w-full h-screen items-center" bind:clientWidth={width} bind:clientHeight={height}>
  <div class="flex flex-col w-full h-full justify-center items-center">
    {#if svgWidth && svgHeight}
      <svg
        class="flex flex-col justify-center items-center overflow-hidden"
        width={svgWidth}
        height={svgHeight}
        id="graph"
      >
        <rect
          width={svgWidth - graphStrokeSize * 2}
          height={svgHeight - graphStrokeSize * 2}
          x={graphStrokeSize}
          y={graphStrokeSize}
          fill="transparent"
          stroke="black"
          stroke-width={graphStrokeSize}
        ></rect>
        {#if data.length}
          <g
            class="non-reactive text-sm"
            transform="translate({xAxisMargin}, {svgHeight - xAxisHeight - xAxisVerticalOffset})"
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
        {/if}
      </svg>
      <div class="absolute">
        <CheckboxFilter value={true} label="Las Vegas Shooting" selection={[true]} />
        <CheckboxFilter value={true} label="Display Observations" selection={[true]} />
        <CheckboxFilter value={true} label="Display Forecasts" selection={[true]} />
      </div>
      <div class="grid grid-cols-2" width={svgWidth}>
        <div class="flex mt-9">
          <span>Metrics</span>
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
        <div class="grid grid-cols-2">
          <div class="w-60 mt-9">
            <Slider
              wrapperClasses="w-fit"
              title="Moving Avergage for Daily Observations"
              items={sliderItems}
              value={0}
              step={1}
              min={0}
              max={sliderItems.length - 1}
              float={true}
              labels={true}
              middle={false}
            />
          </div>
          <div class="w-60 mt-9">
            <Slider
              wrapperClasses="w-fit"
              title="Moving Avergage for Time Series Models"
              items={sliderItems}
              value={0}
              step={1}
              min={0}
              max={sliderItems.length - 1}
              float={true}
              labels={true}
              middle={false}
            />
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

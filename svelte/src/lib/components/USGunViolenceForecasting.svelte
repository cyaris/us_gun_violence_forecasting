<script>
  import * as d3 from "d3"
  import { CheckboxFilter, Select, Slider } from "svelte-lib/components"
  import data from "../static/data.json"

  console.log(data)

  let width
  let height
  let svgWidth
  let svgHeight
  let graphStrokeSize = 1
  $: {
    svgWidth = (width - graphStrokeSize * 2) * 0.65
    svgHeight = (height - graphStrokeSize * 2) * 0.65
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
    { value: "Past", label: "Past" },
    { value: "Future", label: "Future" },
  ]
  let selectValue = { value: "Past", label: "Past" }

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
      </svg>
      <div class="absolute">
        <CheckboxFilter value={true} label="Las Vegas Shooting" selection={[true]} />
        <CheckboxFilter value={true} label="Display Observations" selection={[true]} />
        <CheckboxFilter value={true} label="Display Forecasts" selection={[true]} />
      </div>
      <div class="grid grid-cols-2" width={svgWidth}>
        <div class="flex mt-9">
          <span>Metrics</span>
          <div class="w-24">
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

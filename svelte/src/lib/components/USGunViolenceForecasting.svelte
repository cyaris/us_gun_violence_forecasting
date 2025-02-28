<script>
  import * as d3 from "d3"

  let width
  let height
  let svgWidth
  let svgHeight
  let graphStrokeSize = 2.5
  $: {
    if (width && height) {
      svgWidth = (width - graphStrokeSize * 2) * 0.65
      svgHeight = (height - graphStrokeSize * 2) * 0.65
    }
  }
  fetch(
    "https://raw.githubusercontent.com/cyaris/us_gun_violence_forecasting/refs/heads/master/Web%20Interface/assets/csv/us_gun_violence_forecasting/us_harmed_victim_forecast_data.csv"
  )
    .then(response => response.text())
    .then(csvText => {
      let rows = csvText.trim().split("\n")
      let headers = rows.shift().split(",")

      let json = rows.map(row => {
        let values = row.split(",")
        return headers.reduce((acc, header, i) => {
          acc[header] =
            header == "date"
              ? Date(values[i])
              : ["num_harmed", "year"].includes(header)
                ? parseInt(values[i])
                : parseFloat(values[i])
          acc.index = i
          return acc
        }, {})
      })

      console.log(json)
    })
    .catch(error => console.error("Error fetching CSV:", error))
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
        <rect class="w-full h-full" fill="transparent" stroke="black" stroke-width={graphStrokeSize}></rect>
      </svg>
      <div class="grid grid-cols-2" width={svgWidth}>
        <div class="flex mt-9">
          <span>Metrics</span>
        </div>
        <div class="grid grid-cols-2">
          <div class="flex w-60 mt-9">
            <span>Slider 1</span>
          </div>
          <div class="flex w-60 mt-9">
            <span>Slider 2</span>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

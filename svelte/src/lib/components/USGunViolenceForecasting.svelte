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
    {/if}
  </div>
</div>

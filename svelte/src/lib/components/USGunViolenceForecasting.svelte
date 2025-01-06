<script>
  import * as d3 from "d3"

  let width
  let height
  $: {
    if (width && height) {
      console.log("hi")
    }
  }
</script>

<div class="flex flex-col w-full h-screen items-center" bind:clientWidth={width} bind:clientHeight={height}>
  <div class="flex flex-col w-3/4 h-3/4 justify-center items-center">
    <svg class="w-full h-full" id="graph">
      <g>
        <rect {width} {height} fill="blue"></rect>
      </g>
    </svg>
  </div>
</div>

<script>
  import { LinkButton } from "svelte-lib/components"
</script>

<div class="mb-8 flex min-h-[40vh] flex-col items-center justify-center">
  <LinkButton classes="w-[222.5px]" href="tool" label="Start Forecasting" />
  <div class="mt-2 grid grid-cols-1 gap-x-1 gap-y-2 sm:grid-cols-2">
    <LinkButton classes="w-[222.5px]" href="development" label="Development" />
    <LinkButton classes="w-[222.5px]" href="documentation" label="Documentation" />
  </div>
</div>

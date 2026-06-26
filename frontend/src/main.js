import "../node_modules/svelte-lib/src/lib/static/styles/app.css"
import "../node_modules/svelte-lib/src/lib/static/styles/root.css"

import USGunViolenceForecasting from "./lib/components/USGunViolenceForecasting.svelte"

let div = document.createElement("div")
div.classList.add("us-gun-violence-forecasting")
div.dataset.svelteLibTooltipRoot = "true"

let script = document.currentScript
script.parentNode.insertBefore(div, script)

new USGunViolenceForecasting({ target: div })

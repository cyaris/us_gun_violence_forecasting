import "../node_modules/svelte-lib/src/lib/static/styles/root.css"
import "../node_modules/svelte-lib/src/lib/static/styles/app.css"

import USGunViolenceForecasting from "./lib/components/USGunViolenceForecasting.svelte"

let div = document.createElement("div")
div.classList.add("us-gun-violence-forecasting")

let script = document.currentScript
script.parentNode.insertBefore(div, script)

new USGunViolenceForecasting({
  target: div,
})

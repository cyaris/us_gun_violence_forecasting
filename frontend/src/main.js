import "svelte-lib/styles/app.css"
import "svelte-lib/styles/root.css"

import { mountEmbeddedRoot } from "svelte-lib/functions"

import Router from "./lib/components/Router.svelte"

let div = mountEmbeddedRoot({ classes: ["us-gun-violence-forecasting"], dataset: { svelteLibTooltipRoot: "true" } })

new Router({ target: div })

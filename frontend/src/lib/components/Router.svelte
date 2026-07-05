<script>
  import { Route, Router } from "svelte-routing"

  import Home from "../../routes/+page.svelte"
  import Development from "../../routes/development/+page.svelte"
  import Documentation from "../../routes/documentation/+page.svelte"
  import Tool from "../../routes/tool/+page.svelte"
</script>

<main>
  <Router base="/">
    <Route path="/us_gun_violence_forecasting" component={Home} />
    <Route path="/us_gun_violence_forecasting/development" component={Development} />
    <Route path="/us_gun_violence_forecasting/documentation" component={Documentation} />
    <Route path="/us_gun_violence_forecasting/tool" component={Tool} />
  </Router>
</main>

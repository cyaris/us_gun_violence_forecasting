# Frontend Guidance

## Shared Svelte Conventions

- Use `../../svelte-lib/AGENTS.md` as the source of truth for shared Svelte formatting, config, lint, dependency, D3, Vite, Rollup, CSS import, and scoped embedded styling conventions.
- Keep local guidance focused on `us_gun_violence_forecasting`-specific chart behavior, routes, and Jekyll integration details.

## Frontend Chart Structure

- Use `/us_gun_violence_forecasting` as the simulated GitHub Pages route base. The forecasting tool itself belongs on `src/routes/tool/+page.svelte`.
- Treat hover-based comparison of historical forecast snapshots as the core user workflow. Changes to chart interactions, data shaping, or copy should preserve the ability to compare earlier and later forecasts for the same dates as additional observed data becomes available.
- Keep `USGunViolenceForecasting.svelte` focused on project-specific data, chart state, and markup. Move generic reusable rendering helpers to `svelte-lib` and import them from `svelte-lib/functions` or `svelte-lib/components`.
- In `USGunViolenceForecasting.svelte`, only actual observation points should fade when they exceed the hover year. Model points and all paths should retain their normal full-opacity colors, including in the "Next 365 Days" forecast region.
- Keep forecast-region shading visually behind the chart layers so it does not tint or change the perceived colors of model paths or points.
- Keep sorted/parsed time-series rows and indexed observed/forecast row lists as shared derived data instead of rebuilding them inside layout or pointer-driven reactive blocks.
- Moving-average helpers must preserve row alignment and treat valid `0` values as data. Use finite-value checks rather than truthiness filters for chart paths, points, domains, and trends.
- Cache hover-derived comparative series and model metrics by stable inputs such as prediction column, moving-average window, year, and timeframe.
- Use `drawCanvasCircles` from `svelte-lib/functions` for generic canvas circle rendering instead of recreating project-local point-layer helpers.
- Keep static constants close to use. Inline single-use numeric/static values instead of declaring top-level variables solely for one downstream reference.
- Do not pass fixed/default markup values through helper functions when they can be declared directly in markup.
- Inline trivial event handlers in Svelte markup when they are only used by one element, such as simple hover, mouseleave, or scroll state updates. Use named functions for reused handlers or nontrivial logic.

## Embedded Build

- Keep `data-svelte-lib-tooltip-root` on the Rollup wrapper so body-portal tooltips remain inside the scoped Tailwind CSS.
- Keep Jekyll/Bootstrap-specific rendering overrides out of `USGunViolenceForecasting.svelte` when they do not affect the locally run Svelte app. Put host-page overrides in the Jekyll page stylesheet instead.
- Run `npm run rollup` from `frontend` when changes must affect the Jekyll-rendered bundle; the artifacts are `dist/bundle.js` and `dist/bundle.css`.
- Avoid deriving SVG plot dimensions from the component's own `clientHeight` when that can create circular initial-render sizing. Prefer viewport-based sizing or explicit constraints, and ensure SVG width/height/rect dimensions cannot become negative.

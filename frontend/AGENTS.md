# Frontend Guidance

## Shared Svelte Conventions

- Follow the shared Svelte and JavaScript topics in `../../svelte-lib/agents/`, which `CLAUDE.md` imports:
  - `shared-code.md`
  - `javascript.md`
  - `svelte-components.md`
  - `packages-and-config.md`
  - `embedded-bundles.md`
  - `jekyll-hosting.md`
  - `charts.md`
  - `web-pages.md`

## Routing And Hosting

- Use `/us_gun_violence_forecasting` as the simulated GitHub Pages route base. The forecasting tool itself belongs on `src/routes/tool/+page.svelte`.

## Chart Interaction Semantics

- Treat click-to-pin comparison of historical forecast snapshots as the core user workflow: clicking a chart region pins that year's forecast as the comparison and clicking again clears it, while hovering an eligible region only previews it with an outline. Changes to chart interactions, data shaping, or copy should preserve the ability to compare earlier and later forecasts for the same dates as additional observed data becomes available.
- In `Tool.svelte`, only actual observation points should fade when they exceed the pinned comparison year. Model points and all paths should retain their normal full-opacity colors, including in the "Next 365 Days" forecast region.
- Keep forecast-region shading visually behind the chart layers so it does not tint or change the perceived colors of model paths or points.

## Chart Data Derivations

- Keep sorted/parsed time-series rows and indexed observed/forecast row lists as shared derived data instead of rebuilding them inside layout or pointer-driven reactive blocks.
- Moving-average helpers must preserve row alignment.
- Compare yearly trend values by calendar date, not a fixed row offset. When the current date is February 29 and the
  prior year has no leap day, use February 28 as the prior-year comparison.
- Cache hover-derived comparative series and model metrics by stable inputs such as prediction column, moving-average window, year, and timeframe.

## Embedded Build

- The bundle outputs are `dist/bundle.js` and `dist/bundle.css`.

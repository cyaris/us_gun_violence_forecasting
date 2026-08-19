# Frontend Guidance

## Shared Svelte Conventions

- Use `../../svelte-lib/AGENTS.md` as the source of truth for shared Svelte formatting, config, lint, dependency, D3, Vite, Rollup, CSS import, and scoped embedded styling conventions.

## Local Dependencies

- Keep `linklocal` and local `file:` dependencies in `package.json`; sibling workspace packages such as `svelte-lib` should use `file:../../...` paths.

## Routing And Hosting

- Use `/us_gun_violence_forecasting` as the simulated GitHub Pages route base. The forecasting tool itself belongs on `src/routes/tool/+page.svelte`.

## Chart Interaction Semantics

- Treat hover-based comparison of historical forecast snapshots as the core user workflow. Changes to chart interactions, data shaping, or copy should preserve the ability to compare earlier and later forecasts.
- In `Tool.svelte`, only actual observation points should fade when they exceed the hover year. Model points and all paths should retain their normal full-opacity colors, including in the "Next 36 Months" section.
- Keep forecast-region shading visually behind the chart layers so it does not tint or change the perceived colors of model paths or points.

## Chart Data Derivations

- Keep `Tool.svelte` focused on project-specific data, chart state, and markup. Move generic reusable rendering helpers to `svelte-lib` and import them from `svelte-lib/functions` or `svelte-lib/components`.
- Keep sorted/parsed time-series rows and indexed observed/forecast row lists as shared derived data instead of rebuilding them inside layout or pointer-driven reactive blocks.
- Moving-average helpers must preserve row alignment and treat valid `0` values as data. Use finite-value checks rather than truthiness filters for chart paths, points, domains, and trends.
- Cache hover-derived comparative series and model metrics by stable inputs such as prediction column, moving-average window, year, and timeframe.

## Chart Layout

- Avoid deriving SVG plot dimensions from the component's own `clientHeight` when that can create circular initial-render sizing. Prefer viewport-based sizing or explicit constraints, and ensure SVG containers are explicitly sized.

## Canvas Rendering

- Prefer D3 for calculations and layout logic (scales, interpolation, easing, data transformations, force simulations) and Canvas for the rendering layer. Do not reimplement D3's abstractions in raw JavaScript.
- Separate computation, state management, animation logic, and interaction handling from Canvas drawing operations. Follow an architecture: data → D3 calculations → render-ready data → Canvas drawing.
- Use small, well-named drawing primitives (e.g., `drawCircle`, `drawLine`, `drawPixel`) instead of repeating low-level Canvas commands throughout application code.
- Keep primary render functions declarative and scannable. They should communicate what is being drawn without requiring readers to understand unrelated geometry, animation, or state calculations.
- Calculate geometry and coordinates before drawing. Use meaningful variable names for intermediate values instead of embedding complicated arithmetic inside `fillRect`, `arc`, `moveTo`, or `lineTo` calls.
- Scope Canvas state changes with `ctx.save()` and `ctx.restore()` to prevent transformations, alpha, clipping, or compositing changes from leaking into subsequent drawing operations.
- Keep `requestAnimationFrame` loops small and delegate animation-state updates and rendering to clearly named functions rather than placing substantial logic directly inside the frame callback.
- Model rendered scenes as data (render-ready nodes, links, pixels, labels) so rendering functions consume structured input rather than deriving application state while drawing.
- Avoid abstraction wrappers that merely wrap one or two Canvas calls without improving readability, reuse, or consistency. Drawing helpers should provide meaningful semantic value.
- Preserve readability unless profiling demonstrates that a less-readable implementation provides measurable performance benefits. When performance optimization is necessary, isolate it and document why.
- Prefer generalizable Canvas and D3 utilities in shared libraries when the same behavior is useful across projects rather than recreating equivalent helpers downstream.

## Embedded Build

- Run `npm run rollup` from `frontend` when changes must affect the Jekyll-rendered bundle; the artifacts are `dist/bundle.js` and `dist/bundle.css`.

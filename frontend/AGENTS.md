# Frontend Guidance

## Code Formatting

- Do not use non-functional trailing commas in multiline syntax. Prefer single-line object, call, command, and Svelte markup attribute definitions when they fit under the repository's effective formatter width.
- Prefer single-line formatting for simple parenthesized expressions and arrow callback bodies when they fit within the repository's formatter rules, such as `onMount(() => (mounted = true))`.
- For repository-wide formatting passes, format non-Python files with Prettier using `trailingComma: "none"` and a wide print width so objects/calls are not wrapped solely for style.

## Frontend Chart Structure

- Use `svelte-routing` in `src/lib/components/Router.svelte` to simulate the GitHub Pages paths under `/us_gun_violence_forecasting`. Keep page components in `src/routes` aligned with the static shell pages in `cyaris.github.io/us_gun_violence_forecasting`.
- Keep `src/routes/+page.svelte` as a navigation hub for the app's pages. The forecasting tool itself belongs on `src/routes/tool/+page.svelte`.
- Keep route page content in this source repo. The corresponding pages in `cyaris.github.io` should be lightweight HTML shells that render the compiled app bundle, not duplicated Markdown/content sources.
- Treat hover-based comparison of historical forecast snapshots as the core user workflow. Changes to chart interactions, data shaping, or copy should preserve the ability to compare earlier and later forecasts for the same dates as additional observed data becomes available.
- Keep `USGunViolenceForecasting.svelte` focused on project-specific data, chart state, and markup. Move generic reusable rendering helpers to `svelte-lib` and import them from `svelte-lib/functions` or `svelte-lib/components`.
- In `USGunViolenceForecasting.svelte`, only actual observation points should fade when they exceed the hover year. Model points and all paths should retain their normal full-opacity colors, including in the "Next 365 Days" forecast region.
- Keep forecast-region shading visually behind the chart layers so it does not tint or change the perceived colors of model paths or points.
- Keep sorted/parsed time-series rows and indexed observed/forecast row lists as shared derived data instead of rebuilding them inside layout or pointer-driven reactive blocks.
- Moving-average helpers must preserve row alignment and treat valid `0` values as data. Use finite-value checks rather than truthiness filters for chart paths, points, domains, and trends.
- Cache hover-derived comparative series and model metrics by stable inputs such as prediction column, moving-average window, year, and timeframe.
- Use `drawCanvasCircles` from `svelte-lib/functions` for generic canvas circle rendering instead of recreating project-local point-layer helpers.
- Prefer Tailwind classes over inline styles when the value is static and supported by Tailwind. Avoid Tailwind `!` modifiers unless they are necessary to override external CSS in the rendered Jekyll environment.
- Keep static constants close to use. Inline single-use numeric/static values instead of declaring top-level variables solely for one downstream reference.
- Do not pass fixed/default markup values through helper functions when they can be declared directly in markup.
- Inline trivial event handlers in Svelte markup when they are only used by one element, such as simple hover, mouseleave, or scroll state updates. Use named functions for reused handlers or nontrivial logic.

## Embedded Build

- `src/main.js` is the Rollup entry for the embedded Jekyll/S3 version. It creates the `.us-gun-violence-forecasting` wrapper and mounts `USGunViolenceForecasting`.
- Keep `data-svelte-lib-tooltip-root` on the Rollup wrapper so body-portal tooltips remain inside the scoped Tailwind CSS.
- Keep Jekyll/Bootstrap-specific rendering overrides out of `USGunViolenceForecasting.svelte` when they do not affect the locally run Svelte app. Put host-page overrides in the Jekyll page stylesheet instead.
- The frontend should inherit shared config from `svelte-lib` where available: `svelte.config.js`, `tailwind.config.cjs`, `postcss.config.cjs`, `.prettierrc.cjs`, `eslint.config.js`, and `rollup.config.js`.
- Keep `eslint.config.js` managed by `svelte-lib`; do not replace the re-export with a project-local ESLint configuration. The shared ESLint config assumes ESLint 9 from `svelte-lib`, so refresh `package-lock.json` when shared lint dependencies change.
- Follow the shared `no-use-before-define` convention for JS/CJS files. The shared config intentionally disables this rule for `.svelte` files until `svelte-lib` has a Svelte-aware solution; do not add project-local overrides for it.
- Declare packages imported directly by the frontend in `package.json`; do not rely on `svelte-lib` to provide transitive runtime dependencies for frontend-owned imports.
- When frontend code imports D3 directly, import only the specific `d3-*` subpackages used and declare those subpackages in `package.json`; do not add or import the umbrella `d3` package for frontend-owned code.
- Keep `vite.config.js` as a thin local wrapper around `createViteConfig()` from the package export `svelte-lib/vite.config.js`. Do not import `sveltekit` locally or reach into `../../svelte-lib/src/lib/vite.config.js`; the shared helper owns SvelteKit plugin wiring.
- Import shared CSS in Rollup entry files through `svelte-lib` package exports, such as `svelte-lib/styles/app.css` and `svelte-lib/styles/root.css`. Do not import from `../node_modules/svelte-lib/src/...` source paths.
- Run `npm run rollup` from `frontend` when changes must affect the Jekyll-rendered bundle; the artifacts are `dist/bundle.js` and `dist/bundle.css`.
- Avoid deriving SVG plot dimensions from the component's own `clientHeight` when that can create circular initial-render sizing. Prefer viewport-based sizing or explicit constraints, and ensure SVG width/height/rect dimensions cannot become negative.

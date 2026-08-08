<script>
  import { LinkButton } from "svelte-lib/components"
</script>

<div class="flex flex-col items-center">
  <LinkButton classes="w-56" href="../tool/" label="Start Forecasting" />
</div>

<div class="flex flex-col gap-4">
  <p>
    I started this project soon after the October 2017 shooting in Las Vegas. The whole country was talking about gun
    violence and how bad it had gotten, and that it had gotten bad was never really in question. What I wanted to know
    was narrower: could it have been expected? No forecast is going to call a single event like Las Vegas, but the
    overall level of victims is another matter. If you had stopped in 2015 with only the data available then, how close
    would your forecast have come to the years that followed?
  </p>
  <p>
    That question is what this tool is built to answer. The backend fits a separate model for each year of recorded
    data, one trained through 2014, one through 2015, and so on, and every one of them forecasts the same thing: victims
    injured or killed per day. Hovering over a year on the chart brings back the forecast that year's model made and
    draws it against the observations it never saw, next to the current model and the daily counts we ended up with. The
    metrics underneath report what each model expected in total, per day, and year over year, along with how far its
    predictions landed from what was actually recorded.
  </p>
  <p>
    Reading the models side by side is the whole point. Is the one-year forecast from today in line with the two-year
    forecast made a year ago? Every forecast is revised as new data arrives, so where those revisions moved, and in
    which direction, says as much as any single forecast does on its own.
  </p>
</div>

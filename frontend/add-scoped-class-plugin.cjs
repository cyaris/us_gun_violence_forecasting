module.exports = (opts = { class: "us-gun-violence-forecasting" }) => {
  const scope = `.${opts.class}`

  return {
    postcssPlugin: "add-scoped-class",
    Rule(rule) {
      rule.selectors = rule.selectors.map(selector => (selector == ":root" ? scope : `${scope} ${selector}`))
    },
  }
}

module.exports.postcss = true

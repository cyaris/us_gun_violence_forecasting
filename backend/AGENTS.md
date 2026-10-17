# Backend Guidance

# Inherited Rules

Copied from `../../shared-automation/AGENTS.md` by `sync-agents.js`. Edit them there, then run
`node ../../shared-automation/.github/scripts/sync-agents.js` from this repository's root.

<!-- inherit: shared-automation/python-sql -->
## Python And SQL

These rules add to the Code Style topic for tracked, nonignored Python and SQL source files.

### Python

- Format Python with the repository's Black and isort settings.
- Let isort determine import ordering. Its output takes precedence over manual ordering.
- Leave a blank line immediately before every `return` unless the return is the first statement in the function body, the immediate body of an `if`/`elif`/`else` guard, or immediately follows a multiline string assignment.
- Omit a bare `return` only when control would naturally reach the end of the function at that point. Keep or add a bare `return` for an intentional early exit that prevents later statements from running, and do not write `return None` for a no-value return.
- Follow an `if`/`elif`/`else` statement with a blank line before the next statement unless it is the last statement in its block. A standalone comment immediately after the conditional counts as that separation, so do not also add a blank line before the comment.
- Before formatting, remove trailing commas that serve no syntactic purpose. Keep a comma when syntax requires it or when Black restores it to preserve the formatted layout; judge nested collections independently because Black may collapse them separately.
- Indent the contents of a multiline triple-quoted string to the indentation of its opening delimiter. When the opening delimiter shares a line with a statement, use that statement's indentation; when the delimiter stands on its own as a nested argument, align the contents with the delimiter rather than dedenting them.

### SQL

- Write SQL operations and keywords in lowercase.
- Put each clause, such as `select`, `from`, `where`, `group by`, `order by`, and `limit`, on its own line. A query may remain on one line only when it is a single-item `select` from one table with no other clauses.
- Keep a clause with one item on one line. For multi-item `select` and named-column `group by` clauses, put the keyword on its own line and each item on its own line one indentation level deeper. Keep positional `group by` items inline regardless of count.
- Keep `order by` items inline unless there are at least five named columns or the line would exceed Black's configured line length; then put each item on its own indented line. Positional `order by` items remain inline regardless of count.
- Format an `insert` target-column list as a parenthesized multi-item list with one indented column per line and the closing `)` appended to the last column, followed by a blank line before the supplying `select` or `values`. Lists of three or fewer columns and lists that fit within Black's configured line length may remain inline.
- Treat a single interpolated placeholder that expands to multiple clause items or target columns as one written item: keep it beside the clause keyword or inline within the parentheses.
- For `where`, `having`, and `qualify`, keep a single condition beside the keyword. With multiple conditions, put the keyword on its own line, put each operand on its own indented line, and begin continuation lines with `and` or `or`.
- Break only the outermost boolean level when nested parenthesized groups contain only simple leaf conditions. When a parenthesized group contains another parenthesized boolean group, break that containing group too and indent one additional level per nesting level.
- Prefer `qualify` over a subquery or CTE used only to filter a window function's result.
- Keep a function-call calculation on one line, including an entire window `over (...)` clause and nested aggregate or scalar calls, even when the line is long.
- Keep a join and its first `on` condition on the same line. With multiple join conditions, put each additional condition on its own line, aligned beneath the first condition with the leading `and` or `or` extending to its left.
- Do not alias a query that reads from only one relation. When aliases are needed, assign sequential single-letter aliases `a`, `b`, `c`, and so on in table order, restarting at `a` in each query scope.
- Omit optional operators and keywords that have no effect, including `as` between a selected value and its alias. Retain required syntax such as the `as` in a CTE definition.
- Cast with `::` rather than `cast(... as ...)`.
- In `group by`, use selected-column positions rather than names or calculations whenever possible.
- Put a blank line before a `select` that begins on a new line.
- Prefer a descriptively named CTE over a derived-table subquery in `from` or `join`, but use as few CTEs as practical and fold a one-use projection or simple row-shaping step into its immediate consumer when that remains clear and does not duplicate logic or change table grain.
- Format a `with` clause with `with` on its own line and blank lines after `with`, between CTE definitions, and before the outer query. Write each CTE as `<name> as (` on its own line, leave a blank line before its inner query, keep the inner query at the statement's base indentation, and append the closing `)` and any separating comma to the inner query's final line.
<!-- /inherit: shared-automation/python-sql -->

# Ago examples

A collection of real Ago programs (mostly Advent-of-Code-style daily
solutions) kept as a reference for the language's *style, patterns, and
ethos*. They read input from local files (`a.txt`, `b.txt`, `b`, ...) that are
not checked in, so most are illustrative rather than runnable as-is.

> ⚠️ These are kept **verbatim**, including their warts. Several show off known
> rough edges (precedence quirks, parameter-passing bugs). They are documentation
> of how the language is actually used, not a clean-room test suite. Don't "fix"
> them silently.

## What these demonstrate

### 1. The power of chaining
Ago programs lean heavily on long postfix method chains as a pipeline:

```
apertu("./a.txt").contentes.finderum("\n").mutatuum(des { ... })
```

`apertu` opens a file, `.contentes` grabs its text, `.finderum("\n")` splits it,
`.mutatuum(des{...})` maps a lambda over the result. A whole day's parse +
transform + reduce frequently collapses into a single readable line — see
`12_expr_eval.ago` and `13_columns_pipe.ago` for the extreme cases.

### 2. The ending (suffix) type system — powerful but weird
A variable's **suffix encodes its type**, and referring to the same stem with a
*different* suffix performs a cast:

- `-a` int, `-ae` float, `-am` bool, `-es` string, `-e` range
- `-aem` int-list, `-arum` float-list, `-as` bool-list, `-erum` string-list
- `-uum` list(any), `-ium` any, `-u` struct/map, `-o` lambda/function, `-i` null

So inside a chain `serum` and `sa` and `ses` are "the same value" viewed as a
string-list / int / string respectively. The implicit lambda parameter `id`
gets the same treatment: `ides`, `ida`, `idaem`, `iderum` are `id` cast to
string / int / int-list / string-list. Function and variable *names* must end in
a valid suffix too (the suffix declares the return type), which is why helpers
are named `finderum`, `absium`, `dista`, `betweenam`, etc.

This is the "power but weirdness": casting is invisible and contextual. A value
flows through a pipeline changing type purely by how the next identifier is
spelled. Great for terse code; surprising when a typo in a suffix silently
re-casts instead of erroring.

### 3. Precedence quirks (extra parens that *shouldn't* be needed)
Watch the parenthesization in:

- `01_wraparound_a.ago`: `ca = ca + (non vam).a()` — the `(non vam)` wrap.
- `08_grid_neighbors_a.ago` / `09_grid_stabilize_b.ago`: big guard conditions
  like `si (iia == 0 et jja == 0) vel (...) vel (...)` are fully parenthesized
  because the bare precedence between `et`/`vel`/comparisons doesn't bind the way
  you'd hope.
- `03_palindrome_halves_a.ago`: `ses[0.<(serum.a()/2)]` needs the inner parens
  around the range bound.

These mark spots where the grammar's operator precedence forces parens that a
"natural" reading wouldn't require.

### 4. Parameter-passing bugs
Several files reference a parameter by the *wrong* name/suffix inside a helper —
e.g. in `02_wraparound_b.ago` and `03`, `finderum(les, ...)` then uses
`lerum.a()` (the `-erum` cast of the `les` param) and `rerum.a()` vs a bare `ra`.
These inconsistencies are deliberate breadcrumbs for parameter / suffix-aliasing
bugs in how arguments bind inside function bodies.

## File index

| File | Theme | Highlights |
|------|-------|-----------|
| `01_wraparound_a.ago` | running mod-100 position | `(non vam).a()`, custom `finderum` split |
| `02_wraparound_b.ago` | same, with abs + wrap | `absium`, `ona`/`onam` bool→int |
| `03_palindrome_halves_a.ago` | equal string halves over ranges | range-bound parens, suffix casts |
| `04_repeated_pattern_b.ago` | repeated-substring detection | roman literals `I`/`II`, `pergo`/`frio` |
| `05_recursive_selection.ago` | recursive greedy pick | one-line chain + recursion |
| `06_mergesort_inline_lambda.ago` | inline 2-arg comparator lambda | `des (aium, bium){ ... }` call style |
| `07_roman_range.ago` | roman range + index | `(X..XX)`, `laem[IV]` |
| `08_grid_neighbors_a.ago` | grid neighbour count | heavily parenthesized guards |
| `09_grid_stabilize_b.ago` | iterate grid to fixpoint | `dum verum` + mutation |
| `10_range_membership_a.ago` | count points in ranges | nested `ullam`, `findomnuum` |
| `11_merge_overlapping_ranges_b.ago` | merge overlapping ranges | `inanis` sentinel, `liquum` |
| `12_expr_eval.ago` | one-line expression eval | `proda`/`suma`, `carduum` |
| `13_columns_pipe.ago` | column extraction with `|` | transpose-ish `zuum`, deep chains |
| `14_tree_unique_scribi.ago` | BFS-ish frontier via file IO | `plicium` fold, `scribi`/`apertu` |
| `15_path_counting.ago` | DP path counts | `plicium` fold over rows |
| `16_union_find_a.ago` | union-find via map `.set`/`.get` | `patra`/`conu`, `genorduum` key |
| `17_union_find_b.ago` | union-find via `uu[key]` indexing | same, index syntax variant |
| `18_max_area_adjacency.ago` | max pairwise area | `genorduum(des{-idaem[2]})` descending |
| `19_point_in_polygon.ago` | point-in-polygon ray cast | `ullam`/`omnam`/`liquum`, `betweenam` |

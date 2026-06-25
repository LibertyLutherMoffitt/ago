# Editor integration

All the editor-facing code lives in this repo. What each editor uses differs:

| Feature                 | Neovim                                  | VSCode                                   |
|-------------------------|-----------------------------------------|------------------------------------------|
| Highlighting            | tree-sitter (`tree-sitter-ago/`)        | TextMate grammar (`vscode/syntaxes/`)    |
| Diagnostics/completion/hover/definition/references/rename/formatting | `ago lsp` via `vim.lsp.start` | `ago lsp` via the bundled extension |
| Same-color-by-stem      | semantic tokens **or** `nvim/ago-stem-colors.lua` | semantic tokens (pre-themed in the extension) |

The language server (`ago lsp`) is editor-agnostic and powers everything except
highlighting, so the deep features behave identically in both editors. Only the
highlighting layer differs, because **VSCode does not use tree-sitter for
third-party languages** — it needs a TextMate grammar, which is why there's a
separate one under `vscode/`.

## Guides

- **Neovim (plain):** [`nvim/README.md`](nvim/README.md)
- **Neovim (nixvim):** [`nixvim.md`](nixvim.md) — the grammar is packaged as the
  `tree-sitter-ago` Nix `buildGrammar` output in `flake.nix`.
- **VSCode:** [`vscode/README.md`](vscode/README.md)

## What works in both

- Diagnostics, completion (vars + prelude + builtins), hover (type from ending),
  go-to-definition (stem-aware), find-references (stem-aware), rename (stem-aware,
  ending-preserving), document symbols, and formatting (`ago fmt` via the LSP).
- Same-variable-same-color regardless of ending (semantic tokens in both;
  additionally a tree-walking Lua module for Neovim).

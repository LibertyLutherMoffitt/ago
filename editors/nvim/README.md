# Ago in Neovim

Syntax highlighting via the bundled tree-sitter grammar, plus optional
stem-based identifier coloring.

## 1. Register the file type

```lua
vim.filetype.add({ extension = { ago = "ago" } })
```

## 2. Install the parser

The grammar lives in `tree-sitter-ago/` in this repo (with `src/parser.c`
checked in). With **nvim-treesitter**:

```lua
local parser_config = require("nvim-treesitter.parsers").get_parser_configs()
parser_config.ago = {
  install_info = {
    url = "https://github.com/libertyluthermoffitt/ago", -- or a local path
    location = "tree-sitter-ago",                          -- subdir with grammar
    files = { "src/parser.c" },
    branch = "main",
  },
  filetype = "ago",
}
```

Then `:TSInstall ago`.

Or with plain Nix (no nvim-treesitter): build the parser and point Neovim at it:

```sh
nix build .#tree-sitter-ago     # produces a compiled parser library
```

…and `require("vim.treesitter.language").add("ago", { path = "<built>/parser/ago.so" })`.

## 3. Install the queries

Copy this repo's `tree-sitter-ago/queries/` to `queries/ago/` on your
`runtimepath` (e.g. `~/.config/nvim/queries/ago/`):

```
highlights.scm   locals.scm   folds.scm   indents.scm
```

That gives full syntax highlighting, scope-aware locals, folding and
indentation. (nvim-treesitter ships many languages' queries already; for a
local grammar you supply them yourself as above.)

## 4. (Optional) Same color per variable, regardless of ending

In Ago `xa`, `xes`, `xerum`, `xuum` are the *same* logical variable cast to
different types. Tree-sitter highlight queries can only color by node type, so
they can't make all of those one color. `ago-stem-colors.lua` does: it walks
the tree, strips each identifier's type ending to get its stem, and colors by
stem (hashed into a fixed palette), so one variable is always one color even as
its ending changes.

```lua
-- ensure ago-stem-colors.lua is on your runtimepath / package path
require("ago-stem-colors").setup()   -- auto-attaches to every .ago buffer
```

It layers on top of the normal tree-sitter highlighting (higher priority on
identifiers only), so keywords/strings/numbers keep their usual colors.

(Alternatively, skip this module and let the language server's semantic tokens
do the stem coloring — see step 5.)

## 5. Language server (diagnostics, completion, formatting, …)

The server is editor-agnostic; start it with the built-in client (no lspconfig
needed). `ago` must be on `PATH` (or give the full `python … main.py lsp`).

```lua
vim.api.nvim_create_autocmd("FileType", {
  pattern = "ago",
  callback = function(args)
    vim.lsp.start({ name = "ago-lsp", cmd = { "ago", "lsp" },
                    root_dir = vim.fs.dirname(args.file) })
    -- format on save (the server provides formatting)
    vim.api.nvim_create_autocmd("BufWritePre", {
      buffer = args.buf, callback = function() vim.lsp.buf.format() end,
    })
  end,
})
```

This gives diagnostics, completion (vars + prelude + builtins), hover, go-to
definition / references / rename (all stem-aware), document symbols, and
formatting. For stem coloring via the server's semantic tokens instead of the
Lua module:

```lua
for i = 0, 15 do
  vim.api.nvim_set_hl(0, "@lsp.type.agoStem" .. i, { fg = "#" .. ("..."):rep(1) })
end
```


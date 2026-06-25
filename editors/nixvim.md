# Ago in nixvim

The tree-sitter grammar is already exposed as a Nix `buildGrammar` package
(`packages.tree-sitter-ago` in this repo's `flake.nix`) — the same format
nvim-treesitter consumes — so you can wire everything declaratively.

Assuming you reference this repo's flake as `ago` in your inputs, so that
`ago.packages.${system}.tree-sitter-ago` and the `tree-sitter-ago/queries`
directory are available:

```nix
{ pkgs, inputs, ... }:
let
  agoTs = inputs.ago.packages.${pkgs.system}.tree-sitter-ago;
  agoSrc = inputs.ago;            # the flake source, for the query files
in {
  programs.nixvim = {
    # 1. File type
    extraConfigLua = ''
      vim.filetype.add({ extension = { ago = "ago" } })

      -- Register the grammar with nvim-treesitter
      local parsers = require("nvim-treesitter.parsers").get_parser_configs()
      parsers.ago = { install_info = { url = "none" }, filetype = "ago" }

      -- 3. Language server (no lspconfig entry needed)
      vim.api.nvim_create_autocmd("FileType", {
        pattern = "ago",
        callback = function(args)
          vim.lsp.start({
            name = "ago-lsp",
            cmd = { "ago", "lsp" },               -- or { "python", "/path/main.py", "lsp" }
            root_dir = vim.fs.dirname(args.file),
          })
          -- format on save via the server
          vim.api.nvim_create_autocmd("BufWritePre", {
            buffer = args.buf,
            callback = function() vim.lsp.buf.format() end,
          })
        end,
      })
    '';

    # 2. Grammar + queries placed on the runtimepath
    plugins.treesitter = {
      enable = true;
      grammarPackages = [ agoTs ];
    };
    extraFiles = {
      "parser/ago.so".source = "${agoTs}/parser/ago.so";
      "queries/ago/highlights.scm".source = "${agoSrc}/tree-sitter-ago/queries/highlights.scm";
      "queries/ago/locals.scm".source     = "${agoSrc}/tree-sitter-ago/queries/locals.scm";
      "queries/ago/folds.scm".source      = "${agoSrc}/tree-sitter-ago/queries/folds.scm";
      "queries/ago/indents.scm".source    = "${agoSrc}/tree-sitter-ago/queries/indents.scm";
    };
  };
}
```

(The exact `${agoTs}/parser/ago.so` path is the `buildGrammar` convention; if
your nixvim/nvim-treesitter version places parsers differently, point
`extraFiles."parser/ago.so"` at wherever the derivation puts the `.so`.)

That gets you highlighting, folding, indentation, and the full language server
(diagnostics, completion, hover, go-to-definition, references, rename,
formatting).

## Stem-based identifier coloring

Two options:

1. **Via the server (recommended, zero extra files):** the server emits
   semantic tokens typed `agoStem0..agoStem15` per identifier stem. Map them to
   colors:

   ```lua
   for i = 0, 15 do
     vim.api.nvim_set_hl(0, "@lsp.type.agoStem" .. i, { fg = ... })
   end
   ```

2. **Via the bundled Lua module** (`editors/nvim/ago-stem-colors.lua`), which
   walks the tree-sitter tree directly:

   ```lua
   require("ago-stem-colors").setup()
   ```

Either way `xa`, `xes`, `xerum` all get one color.

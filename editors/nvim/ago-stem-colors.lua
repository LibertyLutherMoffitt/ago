-- ago-stem-colors.lua
--
-- Colors every Ago identifier by its *stem* — the name with its type ending
-- stripped — so that `xa`, `xes`, `xerum`, `xuum` (all the same logical
-- variable in Ago, just cast to different types) get the SAME color, while a
-- different variable gets a different one.
--
-- Tree-sitter highlight queries can't do this (they color by node type and
-- can't compute stem equality), so this walks the tree-sitter tree and applies
-- per-stem highlights via extmarks.
--
-- Usage (after the `ago` parser + queries are installed, see README.md):
--   require("ago-stem-colors").setup()        -- auto-attach to *.ago buffers
-- or, manually per buffer:
--   require("ago-stem-colors").attach(bufnr)

local M = {}

local ns = vim.api.nvim_create_namespace("ago_stem_colors")

-- Ago type endings, longest first, so the longest valid suffix is stripped.
local SUFFIXES = {
  "arum", "erum", "aem", "uum", "ium",
  "ae", "es", "am", "as",
  "a", "e", "i", "o", "u",
}

-- A pleasant, distinguishable palette. Stems hash into this deterministically.
local COLORS = {
  "#e06c75", "#98c379", "#e5c07b", "#61afef", "#c678dd", "#56b6c2",
  "#d19a66", "#be5046", "#7fbf7f", "#c9a36b", "#5fb3b3", "#a3a1f7",
  "#f08fc0", "#86b300", "#00a3cc", "#cc8800",
}

local function ensure_groups()
  for i, c in ipairs(COLORS) do
    vim.api.nvim_set_hl(0, "AgoStem" .. i, { fg = c })
  end
end

local function stem(name)
  for _, s in ipairs(SUFFIXES) do
    if #name > #s and name:sub(-#s) == s then
      return name:sub(1, #name - #s)
    end
  end
  return name
end

-- djb2 hash -> palette index (1-based).
local function color_index(s)
  local h = 5381
  for i = 1, #s do
    h = (h * 33 + s:byte(i)) % 2147483648
  end
  return (h % #COLORS) + 1
end

function M.highlight(bufnr)
  bufnr = bufnr or vim.api.nvim_get_current_buf()
  local ok, parser = pcall(vim.treesitter.get_parser, bufnr, "ago")
  if not ok or not parser then
    return
  end
  vim.api.nvim_buf_clear_namespace(bufnr, ns, 0, -1)
  local root = parser:parse()[1]:root()
  local query = vim.treesitter.query.parse("ago", "(identifier) @id")
  for _, node in query:iter_captures(root, bufnr, 0, -1) do
    local text = vim.treesitter.get_node_text(node, bufnr)
    if text and #text > 0 then
      local grp = "AgoStem" .. color_index(stem(text))
      local sr, sc, er, ec = node:range()
      pcall(vim.api.nvim_buf_set_extmark, bufnr, ns, sr, sc, {
        end_row = er,
        end_col = ec,
        hl_group = grp,
        priority = 200, -- above tree-sitter @variable highlighting
      })
    end
  end
end

function M.attach(bufnr)
  bufnr = bufnr or vim.api.nvim_get_current_buf()
  ensure_groups()
  M.highlight(bufnr)
  vim.api.nvim_create_autocmd({ "TextChanged", "TextChangedI", "BufEnter" }, {
    buffer = bufnr,
    callback = function()
      M.highlight(bufnr)
    end,
  })
end

function M.setup()
  ensure_groups()
  vim.api.nvim_create_autocmd("FileType", {
    pattern = "ago",
    callback = function(args)
      M.attach(args.buf)
    end,
  })
end

return M

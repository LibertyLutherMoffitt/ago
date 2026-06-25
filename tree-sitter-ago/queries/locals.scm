; Scope/definition/reference tracking for nvim-treesitter's `locals` module.
; (Links *exact* same-name occurrences; for same-stem-across-endings coloring
; see editors/nvim/ago-stem-colors.lua, which the query engine cannot express.)

; ---- Scopes ----
[
  (function_definition)
  (lambda)
  (block)
] @local.scope

; ---- Definitions ----
(function_definition name: (identifier) @local.definition.function)
(declaration name: (identifier) @local.definition.var)
(for_statement iterator: (identifier) @local.definition.var)

; ---- References ----
(identifier) @local.reference

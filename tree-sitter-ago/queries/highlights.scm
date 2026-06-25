; Tree-sitter syntax highlighting queries for Ago.
; More specific patterns come first; the generic (identifier) fallback is last.

; ---- Comments ----
(comment) @comment

; ---- Literals ----
(int) @number
(float) @number.float
(roman_numeral) @number
(string) @string
[
  (true)
  (false)
] @boolean
(null) @constant.builtin
(it) @variable.builtin

; ---- Functions ----
(function_definition name: (identifier) @function)
(call function: (identifier) @function.call)
(method_call name: (identifier) @function.method.call)

; ---- Map keys ----
(pair key: (identifier) @property)

; ---- Keywords ----
[
  "si"
  "aluid"
  "discerne"
] @keyword.conditional

[
  "pro"
  "dum"
] @keyword.repeat

; frio/pergo/omitto are keyword-only statements (the whole node is the keyword).
[
  (break_statement)
  (continue_statement)
] @keyword.repeat

(pass_statement) @keyword

"redeo" @keyword.return

"des" @keyword.function

[
  "in"
  "est"
  "et"
  "vel"
  "non"
] @keyword.operator

; ---- Operators ----
[
  "+" "-" "*" "/" "%"
  "==" "!=" "<" ">" "<=" ">="
  "&" "|" "^" ".." ".<" "?:"
  "=" ":=" "+=" "-=" "*=" "/=" "%="
  "?" ":"
] @operator

; ---- Punctuation ----
[
  "(" ")"
  "[" "]"
  "{" "}"
] @punctuation.bracket

[
  ","
  "."
] @punctuation.delimiter

; ---- Variables (fallback) ----
(identifier) @variable

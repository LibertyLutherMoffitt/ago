# Learn Ago

Ago is a small Latin-inspired language that compiles to Rust. This tutorial
walks through the whole language from "hello world" to pattern matching. For a
full catalogue of every callable (builtins, prelude functions, and the cast
methods) and where its source lives, see [`functions.md`](functions.md).

## 1. Running a program

Write your code in a `.ago` file and run it:

```sh
python main.py hello.ago          # compile (debug) and run
python main.py hello.ago --release  # optimized build
python main.py hello.ago --check    # type-check only, don't run
ago fmt hello.ago                   # format in place
ago fmt src/                        # format every .ago file under src/ recursively
```

The first program:

```ago
dici("salve, munde")
```

`dici` prints a line to stdout. Running it prints `salve, munde`.

## 2. Variables and the suffix type system

This is the one idea that makes Ago unusual: **a variable's type is encoded in
the ending of its name**, not declared separately. The "stem" is the name minus
its suffix, and you may only have one variable per stem.

```ago
counta := 0          # -a   -> int
ratioae := 3.5       # -ae  -> float
flagam := verum      # -am  -> bool
namees := "Marcus"   # -es  -> string
numsaem := [1, 2, 3] # -aem -> int list
```

`:=` declares a new variable; `=` reassigns an existing one. Booleans are
`verum` (true) and `falsus` (false); the null value is `inanis`.

The full suffix table:

| suffix | type | suffix | type |
|---|---|---|---|
| `-a` | int | `-erum` | string list |
| `-ae` | float | `-uum` | any list |
| `-am` | bool | `-u` | map / struct |
| `-es` | string | `-e` | range |
| `-aem` | int list | `-ium` | any |
| `-arum` | float list | `-i` | null (functions with side effects) |
| `-as` | bool list | `-o` | function |

Because the suffix *is* the type, the same stem refers to "the same value
viewed as a different type." Casting (section 7) just changes the suffix.

## 3. Output and input

```ago
dici("quaere nomen:")
namees := audies()          # read one line from stdin
dici("salve, " + namees)
```

`audies` returns a string (its `-es` ending tells you so). To print a number,
convert it to a string first with `.es()` (see casting).

## 4. Arithmetic, comparison, and logic

```ago
suma := 2 + 3 * 4       # 14
resta := 10 - 7         # 3
quota := 17 / 5         # 3  (integer division for ints)
moda := 17 % 5          # 2
powae := 2.0 ** 10.0    # 1024.0
```

Comparisons (`==`, `!=`, `<`, `<=`, `>`, `>=`) produce bools. The logical
operators are words: `et` (and), `vel` (or), `non` (not).

```ago
okam := (xa > 0) et (xa < 100)
anyam := aam vel bam
negam := non flagam
```

Compound assignment works too: `+=`, `-=`, `*=`, `/=`, `%=`.

## 5. Strings and interpolation

Strings concatenate with `+`. Inside a string literal, `${ ... }` splices in
any expression (converting it to text automatically):

```ago
namees := "Marcus"
agea := 42
dici("salve, ${namees}! age = ${agea}")
dici("summa = ${2 + 3 * 4}")
dici("nested ${"quote " + namees}")   # quotes nest inside ${ }
```

## 6. Lists and maps

Lists are written with `[]` and indexed from 0. Negative indices count from the
end. Slices use a range index.

```ago
xsaem := [10, 20, 30, 40]
firsta := xsaem[0]        # 10
lasta  := xsaem[-1]       # 40
heaaem := xsaem[0.<2]     # [10, 20]   (half-open range)
lena   := xsaem.a()       # 4          (length, via the int cast)
```

Maps/structs use the `-u` ending and `{}` literals; missing keys return
`inanis` rather than crashing:

```ago
ageu := {"Marcus": 42, "Livia": 30}
ma := ageu["Marcus"]      # 42
missingi := ageu["Nemo"]  # inanis
```

## 7. Casting with `.x()` methods

Every type can be converted to another by calling the method named for the
**target suffix**. These are the "magic methods":

```ago
sa := "123".a()      # string -> int      123
ses := 123.es()      # int -> string      "123"
fae := 3.ae()        # int -> float       3.0
ia := 3.7.a()        # float -> int       3   (truncates)
lena := xsaem.a()    # list -> int        (length)
```

The complete list of cast methods is in
[`functions.md`](functions.md#cast-methods-x). They are implemented by
`AgoType::as_type` in `src/rust/src/casting.rs`.

## 8. Control flow

### si / aluid (if / else)

```ago
si xa > 0 {
    dici("positive")
} aluid xa == 0 {        # else-if is `aluid <cond> {`, with no `si`
    dici("zero")
} aluid {                # bare `aluid {` is the final else
    dici("negative")
}
```

### The ternary `?:`

`cond ? a : b` is an expression. It also doubles as null-coalescing, since
`inanis` is falsy:

```ago
da := sleftuum[ia] - srightuum[ia]
absa := da >= 0 ? da : 0 - da
namees := ageu["Nemo"] ? ageu["Nemo"] : "(unknown)"
```

### dum (while)

```ago
ia := 0
dum ia < 5 {
    dici(ia.es())
    ia += 1
}
```

### pro (for)

Iterate over a range or a list. Ranges are `start.<end` (half-open) and support
descending/step forms.

```ago
pro ia in 0.<5 {            # 0,1,2,3,4
    dici(ia.es())
}

pro namees in ["a", "b", "c"] {
    dici(namees)
}
```

Dual binding **without parentheses** gives you index + value (enumerate) when
iterating a list, or key + value over a map:

```ago
pro ia, vees in ["x", "y", "z"] {
    dici("${ia}: ${vees}")     # 0: x, 1: y, 2: z
}
```

Dual binding **with parentheses** destructures, when each item is itself a pair:

```ago
pairsuum := [[1, 2], [3, 4]]
pro (aa, ba) in pairsuum {
    dici("${aa}+${ba} = ${aa + ba}")
}
```

`frio` breaks out of a loop; `pergo` continues to the next iteration.

### discerne (pattern match)

A value-equality multi-way branch. Each arm is `pattern { ... }`, and `aluid`
is the catch-all:

```ago
discerne na {
    1 { dici("unus") }
    2 { dici("duo") }
    aluid { dici("multi") }
}
```

## 9. Functions and lambdas

Named functions use `des name(params) { ... }` and return with `redeo`. The
function's own suffix advertises its return type (`-a` returns int, `-i` means
"no meaningful value / side effects only").

```ago
des addia(pa, qa) {
    redeo pa + qa
}
dici(addia(2, 3).es())     # 5
```

Functions are first class. An anonymous lambda is `des { ... }`; inside it the
implicit argument is `id` (and `iderum`, `idaem`, ... for the typed views of
the same value). Lambdas shine with the list-processing prelude functions:

```ago
doubaem := [1, 2, 3].mutatuum(des { id * 2 })     # [2, 4, 6]
evenaem := [1, 2, 3, 4].liquum(des { id % 2 == 0 }) # [2, 4]
totala  := [1, 2, 3, 4].suma()                     # 10
```

You can also pass a named function where a lambda is expected.

Self-recursion in tail position is automatically turned into a loop, so
accumulator-style recursion runs in constant stack space:

```ago
des sumupa(na, acca) {
    si na == 0 { redeo acca }
    redeo sumupa(na - 1, acca + na)   # tail call -> compiled to a loop
}
dici(sumupa(1000000, 0).es())          # no stack overflow
```

## 10. The pipeline style

Method calls chain left to right, which reads like a Unix pipeline. This is the
idiomatic Ago style for data wrangling:

```ago
apertu("in.txt").contentes
    .finderum("\n")               # split into lines
    .mutatuum(des { id.a() })     # parse each to int
    .liquum(des { id > 0 })       # keep positives
    .sumes()                      # sum
    .dici()                       # print
```

`apertu` opens a file and returns a struct with `.contentes` (text),
`.filenames`, and `.filesizea`.

## 11. Where to go next

- [`functions.md`](functions.md) — every builtin, prelude function, and cast
  method, with a description and a link to its source.
- `examples/` — small, complete programs.
- `aoc/2024/` — fuller solutions (Advent of Code) showing real-world idioms.
- `stdlib/prelude.ago` — the standard library, written in Ago itself; a good
  read once the basics click.

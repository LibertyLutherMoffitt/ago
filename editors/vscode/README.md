# Ago for VSCode

Syntax highlighting (TextMate) plus the full Ago language server: diagnostics,
completion, hover, go-to-definition, find-references, rename, formatting, and
stem-based identifier coloring (via semantic tokens, pre-themed in
`package.json`).

VSCode does not use tree-sitter for third-party languages, so highlighting here
comes from `syntaxes/ago.tmLanguage.json`; the deeper features all come from the
language server, which is editor-agnostic.

## Prerequisites

`ago` must be runnable and on your `PATH` (so `ago lsp` starts the server). If
it isn't, set the command explicitly in settings:

```json
{
  "ago.serverCommand": "python",
  "ago.serverArgs": ["/path/to/ago/main.py", "lsp"]
}
```

## Run from source

```sh
cd editors/vscode
npm install
code .
# press F5 to launch an Extension Development Host
```

Open any `.ago` file. You should get highlighting immediately and, once the
server connects, diagnostics/completion/hover/etc.

## Package / install

```sh
cd editors/vscode
npm install -g @vscode/vsce
vsce package          # produces ago-0.1.0.vsix
code --install-extension ago-0.1.0.vsix
```

## Stem coloring

The server emits semantic tokens typed `agoStem0..agoStem15` by each
identifier's stem, and this extension ships default colors for them
(`editor.semanticTokenColorCustomizations` in `package.json`), so `xa`, `xes`,
`xerum` all share one color out of the box. Override the palette in your
settings if you like.

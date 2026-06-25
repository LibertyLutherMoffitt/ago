// Ago VSCode extension: starts the Ago language server and connects to it.
//
// Syntax highlighting comes from the bundled TextMate grammar
// (syntaxes/ago.tmLanguage.json). Everything else — diagnostics, completion,
// hover, go-to-definition, references, rename, formatting, and stem-based
// semantic-token coloring — comes from the language server (`ago lsp`).

const { workspace } = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function activate(context) {
  const cfg = workspace.getConfiguration("ago");
  const command = cfg.get("serverCommand") || "ago";
  const args = cfg.get("serverArgs") || ["lsp"];

  const serverOptions = {
    run: { command, args, transport: TransportKind.stdio },
    debug: { command, args, transport: TransportKind.stdio },
  };

  const clientOptions = {
    documentSelector: [{ scheme: "file", language: "ago" }],
    synchronize: {
      fileEvents: workspace.createFileSystemWatcher("**/*.ago"),
    },
  };

  client = new LanguageClient(
    "ago",
    "Ago Language Server",
    serverOptions,
    clientOptions
  );
  client.start();
  context.subscriptions.push(client);
}

function deactivate() {
  return client ? client.stop() : undefined;
}

module.exports = { activate, deactivate };

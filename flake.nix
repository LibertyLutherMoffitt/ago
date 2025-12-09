{
  description = "Ago - A Latin-inspired programming language that transpiles to Python";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs @ {flake-parts, ...}:
    flake-parts.lib.mkFlake {inherit inputs;} {
      systems = ["x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin"];

      perSystem = {pkgs, self', ...}: let
        # Python environment with dependencies
        pythonEnv = pkgs.python3.withPackages (p: with p; [tatsu pytest pytest-xdist tkinter]);
        
        # Version
        version = "0.2.0";
      in {
        # The main Ago CLI package
        packages.default = pkgs.stdenv.mkDerivation {
          pname = "ago";
          inherit version;
          
          src = ./.;
          
          nativeBuildInputs = [
            pkgs.makeWrapper
          ];
          
          installPhase = ''
            mkdir -p $out/bin $out/lib/ago $out/share/ago
            
            # Copy source files needed at runtime
            cp -r src $out/lib/ago/
            cp main.py $out/lib/ago/
            
            # Copy stdlib (Ago standard library prelude)
            cp -r stdlib $out/lib/ago/
            
            # Create the main wrapper script
            makeWrapper ${pythonEnv}/bin/python3 $out/bin/ago \
              --add-flags "$out/lib/ago/main.py" \
              --set AGO_HOME "$out/lib/ago"
            
            # Create shell completions directory
            mkdir -p $out/share/bash-completion/completions
            mkdir -p $out/share/zsh/site-functions
            mkdir -p $out/share/fish/vendor_completions.d
            
            # Bash completion
            cat > $out/share/bash-completion/completions/ago <<'BASH'
_ago() {
    local cur prev opts
    COMPREPLY=()
    cur="''${COMP_WORDS[COMP_CWORD]}"
    prev="''${COMP_WORDS[COMP_CWORD-1]}"
    opts="--help --version --check --emit --ast --no-color --quiet"
    
    case "$prev" in
        --emit)
            COMPREPLY=( $(compgen -W "python" -- "$cur") )
            return 0
            ;;
    esac
    
    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
    else
        COMPREPLY=( $(compgen -f -X '!*.ago' -- "$cur") )
    fi
}
complete -F _ago ago
BASH
            
            # Zsh completion
            cat > $out/share/zsh/site-functions/_ago <<'ZSH'
#compdef ago

_ago() {
    _arguments \
        '1:ago file:_files -g "*.ago"' \
        '--help[Show help message]' \
        '--version[Show version]' \
        '--check[Only run semantic checks]' \
        '--emit[Emit output type]:type:(python)' \
        '--ast[Print parsed AST]' \
        '--no-color[Disable colored output]' \
        '-q[Suppress info messages]' \
        '--quiet[Suppress info messages]'
}

_ago "$@"
ZSH
            
            # Fish completion
            cat > $out/share/fish/vendor_completions.d/ago.fish <<'FISH'
complete -c ago -f
complete -c ago -a '(__fish_complete_suffix .ago)'
complete -c ago -l help -d 'Show help message'
complete -c ago -l version -d 'Show version'
complete -c ago -l check -d 'Only run semantic checks'
complete -c ago -l emit -d 'Emit output type' -xa 'python'
complete -c ago -l ast -d 'Print parsed AST'
complete -c ago -l no-color -d 'Disable colored output'
complete -c ago -s q -l quiet -d 'Suppress info messages'
FISH
            
            # Man page
            mkdir -p $out/share/man/man1
            cat > $out/share/man/man1/ago.1 <<'MAN'
.TH AGO 1 "2024" "ago ${version}" "User Commands"
.SH NAME
ago \- A Latin-inspired programming language that transpiles to Python
.SH SYNOPSIS
.B ago
.RI [ OPTIONS ]
.I FILE
.SH DESCRIPTION
Ago is a programming language with Latin-inspired syntax that compiles to Python.
It features a unique type system where variable name endings indicate types, though this is not enforced in the Python backend.
.SH OPTIONS
.TP
.B \-\-check
Only run semantic checks without compiling or running.
.TP
.B \-\-emit=python
Emit generated Python source code to standard output.
.TP
.B \-\-ast
Print the parsed AST in JSON format (for debugging).
.TP
.B \-\-no\-color
Disable colored terminal output.
.TP
.B \-q, \-\-quiet
Suppress informational messages.
.TP
.B \-v, \-\-version
Show version information.
.TP
.B \-h, \-\-help
Show help message.
.SH EXAMPLES
.TP
Run an Ago program:
.B ago hello.ago
.TP
Check for errors without running:
.B ago hello.ago \-\-check
.TP
Generate Python code:
.B ago hello.ago \-\-emit=python > hello.py
.SH AUTHOR
Written by LLM.
.SH BUGS
Report bugs at: https://github.com/libertyluthermoffitt/ago/issues
.SH COPYRIGHT
MIT License
MAN
          '';
          
          meta = with pkgs.lib; {
            description = "A Latin-inspired programming language that transpiles to Python";
            homepage = "https://github.com/libertyluthermoffitt/ago";
            license = licenses.mit;
            maintainers = [];
            mainProgram = "ago";
          };
        };

        # Format script - runs ruff format and check
        packages.fmt = pkgs.writeShellScriptBin "ago-fmt" ''
          set -e
          cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
          
          echo "🔧 Formatting Python with ruff..."
          ${pkgs.ruff}/bin/ruff format .
          
          echo "🔧 Fixing Python lint issues with ruff..."
          ${pkgs.ruff}/bin/ruff check --fix . || true
          
          echo "✅ Done!"
        '';
        
        # Check script - runs formatters in check mode
        packages.check-fmt = pkgs.writeShellScriptBin "ago-check-fmt" ''
          set -e
          cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
          
          echo "🔍 Checking Python formatting..."
          ${pkgs.ruff}/bin/ruff format --check .
          
          echo "🔍 Checking Python lint..."
          ${pkgs.ruff}/bin/ruff check .
          
          echo "✅ All checks passed!"
        '';

        # Development shell
        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv
            pkgs.ruff
            pkgs.pyright
            self'.packages.default  # Make 'ago' command available
          ];
          
          shellHook = ''
            echo "🏛️  Ago Development Shell (Python Backend)"
            echo "   Run ago:     ago <file.ago>"
            echo "   Run tests:   pytest test/"
            echo "   Format:      nix run .#fmt"
            echo "   Check fmt:   nix run .#check-fmt"
          '';
        };
      };
    };
}

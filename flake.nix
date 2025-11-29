{
  description = "rust + python";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs @ {flake-parts, ...}:
    flake-parts.lib.mkFlake {inherit inputs;} {
      systems = ["x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin"];

      perSystem = {pkgs, ...}: let
        # 1. Define the Python environment once so we can reuse it
        pythonEnv = pkgs.python3.withPackages (p: with p; [tatsu pytest tkinter]);
      in {
        # 2. The Build Output (nix build)
        # This creates a tool that takes a file, runs python on it, then runs rustc
        packages.default = pkgs.stdenv.mkDerivation {
          name = "ago";

          # Copy the current directory (including src/main.py)
          src = ./.;

          # No build dependencies needed at this stage,
          # because we are just packaging the script and source.
          nativeBuildInputs = [pkgs.cargo];

          buildPhase = "true"; # Skip build phase

          # Create the wrapper script
          installPhase = ''
            mkdir -p $out/bin $out/libexec

            # Copy the source code (src/main.py) to a permanent location in the store
            cp -r src $out/libexec/src

            # Build the Rust standard library
            # We need to change directory to src/rust where Cargo.toml is located
            (cd $out/libexec/src/rust && ${pkgs.cargo}/bin/cargo build --release)

            # Get the path to the compiled Rust library
            # Assuming the library is named libago_stdlib.rlib
            RUST_STDLIB_PATH=$out/libexec/src/rust/target/release/libago_stdlib.rlib

            # Generate the executable script 'ago'
            cat > $out/bin/ago <<EOF
            #!/bin/bash
            set -e

            if [ "\$#" -ne 1 ]; then
                echo "Usage: ago <input_file>"
                exit 1
            fi

            INPUT_FILE="\$1"
            OUTPUT_BIN="''${INPUT_FILE%.*}"
            TEMP_RS="temp.rs"

            echo "Transpiling \$INPUT_FILE to Rust..."
            # Run the python script using the specific pythonEnv
            # We reference the absolute path to main.py inside the nix store ($out)
            ${pythonEnv}/bin/python3 $out/libexec/src/main.py "\$INPUT_FILE" > "\$TEMP_RS"

            echo "Compiling Rust binary..."
            # Run rustc using the specific rustc from pkgs
            # Link against the ago_stdlib
            ${pkgs.rustc}/bin/rustc "\$TEMP_RS" -o "\$OUTPUT_BIN" --extern ago_stdlib="\$RUST_STDLIB_PATH"

            echo "Done! executable created at ./\$OUTPUT_BIN"
            rm "\$TEMP_RS"
            EOF

            chmod +x $out/bin/ago
          '';
        };

        # 3. The Development Shell (nix develop)
        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv
            pkgs.rustc
            pkgs.ruff
            pkgs.pyright
            pkgs.rustfmt
          ];
        };
      };
    };
}

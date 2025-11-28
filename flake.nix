{
  description = "rust + python";
  inputs.unstable.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  outputs = inputs: let
    system = "x86_64-linux";
    pkgs = import inputs.unstable {inherit system;};
  in {
    devShells.${system} = {
      default = pkgs.mkShell {
        packages = with pkgs; [
          (python3.withPackages (p: with p; [tatsu]))
          rustc
        ];
      };
    };
  };
}

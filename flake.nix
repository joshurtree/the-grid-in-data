{
  description = "Nix flake for GB Electricity Prices - Gradio web interface";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }:
  let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
  in {
    apps.${system}.app = {
      type = "app";
      program = "uv";
      args = [ "run" "app.py" ];
    };

    devShells.${system}.default = pkgs.mkShell {
      buildInputs = with pkgs; [ 
        git
        python313 
        python313Packages.numpy
        uv
      ];
      
      shellHook = ''
        echo "✓ Nix environment loaded with Python 3.13, uv, git, and poetry"
        echo ""
        echo "Quick start:"
        echo "  uv sync              # Install dependencies from pyproject.toml"
        echo "  uv run app.py        # Run the Gradio web interface on http://localhost:7860"
        echo "  nix run .#app        # Run with flake"
      '';
    };
  };
}

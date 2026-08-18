{
  description = "Nix flake for GB Electricity Prices - Streamlit web interface";

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
      args = [ "run" "streamlit" "run" "app.py" ];
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
        echo "  uv sync                          # Install dependencies from pyproject.toml"
        echo "  uv run streamlit run Home.py     # Run the Streamlit web interface on http://localhost:8501"
        echo "  uv run fetch-data.py                 # Fetch the latest data from the NESO and LCCC APIs"
        echo "  nix run .#app                    # Run with flake"
      '';
    };
  };
}


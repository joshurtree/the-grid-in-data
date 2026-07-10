{
  description = "Nix flake for running gbwep.py with taipy (installed via pip from GitHub source)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }:
  let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
  in {
    apps.${system}.gbgridtracker = {
      type = "app";
      program = "uv";
      args = [ "run", "${toString ./.}/main.py" ];
    };

    devShells.${system}.default = pkgs.mkShell {
      buildInputs = with pkgs; [ 
        git
        python312 
        python312Packages.numpy
        uv
      ];
    };
  };
}

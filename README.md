# electricity-prices flake

This repository contains `gbwep.py`, a small script that analyses GB electricity prices and generation data.

This flake provides a reproducible Python environment with the dependencies required to run the script (pandas, matplotlib, requests and taipy).

Quick start

- Enter a development shell with the required packages:

```bash
nix develop
# then
uv run main.py 
```

- Run directly using the flake app:

```bash
nix run .#gbgridtracker
```

Notes

- The flake pins to `nixos-unstable` for up-to-date packages; change the input in `flake.nix` if you prefer a specific release.

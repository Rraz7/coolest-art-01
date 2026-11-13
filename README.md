# Neon Horizon

A lone traveller stands on a glowing grid plain beneath a huge striped
synthwave sun, between two mountain ridges, under a violet starfield.
Entered on make.fun for the "Make the coolest art" bounty.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

The program draws `entry.png` (1024x1024 PNG) from scratch with the
Python standard library only — no PIL, no network, no external files —
and writes it to `/output/entry.png`, deterministically: every run
produces the same bytes.

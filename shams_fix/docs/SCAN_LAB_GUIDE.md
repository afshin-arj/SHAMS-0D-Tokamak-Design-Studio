# SHAMS — Scan Lab Guide

Author: © 2026 Afshin Arjhangmehr

Scan Lab is SHAMS' 0-D design space map-maker. It helps you see what limits a design, where, and why.

## Core rule

Point Designer defines truth. Scan Lab maps truth.

## What Scan Lab is (and is not)

Scan Lab DOES:
- Evaluate the frozen Point Designer model on a set of points (grid, sparse, or path)
- Produce constraint-dominance cartography, first-failure topology, intent split maps, and robustness labels
- Generate structured narratives based on scan statistics

Scan Lab DOES NOT:
- Optimize, search, rank, or recommend designs
- Relax constraints or change thresholds
- Modify Point Designer physics

## How to run a standard 2-D scan

1) Choose baseline
- Start from a reference preset or your current Point Designer inputs.

2) Choose axes
- Pick x-axis and y-axis keys (Ip, R0, Bt, fG, etc.).

3) Choose bounds and resolution
- Set min/max for each axis.
- Use Nx, Ny to set resolution.

4) Choose intent lens
- Reactor: all hard constraints are blocking.
- Research: q95 remains blocking; TBR is ignored; most engineering limits are diagnostic.

5) Run
- Use the progress indicator to track point rate and ETA.

## How to read the dominance map

Each cell is colored by the dominant blocking constraint (worst margin among blocking hard constraints).
- Uniform regions: one constraint dominates.
- Color boundaries: regime transitions.

## How to use first-failure topology

Click a cell and inspect:
- Failure order (worst to less-worst)
- Blocking vs diagnostic vs ignored lists (intent-aware)

## Robustness labels

Robust / Balanced / Brittle / Knife-edge reflect the local neighborhood feasible fraction.
This is descriptive only (no ranking or recommendation).

## Exports

Scan Lab exports:
- JSON scan artifact (schema v1)
- CSV point table (optional)
- PNG maps
- A fixed-length 10-page Scan Lab Atlas (signature artifact)

## Citing Scan Lab

Use the auto-generated citation string included in exports, which embeds:
- SHAMS version
- Point Designer fingerprint
- scan id and report hash

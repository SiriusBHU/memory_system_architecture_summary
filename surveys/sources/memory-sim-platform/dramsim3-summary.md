# DRAMSim3: Cycle-Accurate, Thermal-Capable DRAM Simulator — Summary

> Source paper: Li, S. et al. "DRAMsim3: A Cycle-Accurate, Thermal-Capable DRAM Simulator."
> IEEE Computer Architecture Letters, 2020.
> URL: https://dl.acm.org/doi/10.1109/LCA.2020.2973991
> GitHub: https://github.com/umd-memsys/DRAMsim3

## Overview

DRAMSim3 is a cycle-accurate DRAM simulator offering the best simulation performance and feature sets among existing cycle-accurate DRAM simulators at the time of publication. It is also the first DRAM simulator to offer runtime thermal modeling alongside performance modeling.

## Architecture Components

DRAMSim3 features a modular hierarchy:

- **Channels**: Top-level memory channels
- **Ranks**: Per-channel rank organization
- **Bank Groups**: DDR4+ bank group modeling
- **Banks**: Individual bank state machines

Each represented by dedicated C++ classes, with timing parameters (tRCD, tRP, tRAS, etc.) loaded from JSON configuration files to match specific DRAM standards.

## Key Features

### Command Scheduling
Built-in memory controller supports configurable scheduling policies:
- FCFS (First-Come-First-Served)
- FRFCFS (First-Ready-First-Come-First-Served)
- Per-bank command queues with arbitration logic to model realistic contention and bank-level parallelism

### Thermal Modeling
Runtime thermal modeling integrated with performance simulation — first DRAM simulator to offer this combination.

### Power Analysis
Uses Micron's DRAM power model to calculate power consumption on the fly, including:
- Active/precharge power
- Refresh power
- Power-down modes (self-refresh)

### Refresh Modeling
Periodic and on-idle refresh operations modeled according to tREFI and tRFC parameters, including power-down self-refresh modes for low-power analysis.

## Supported DRAM Standards

- DDR4
- LPDDR4
- HBM2
- (Configurable for other standards via JSON timing files)

## Operating Modes

1. **Standalone trace-driven**: Drive with address-trace files for microbenchmarks
2. **Integrated mode**: Hot-plug interfaces to full-system simulators (gem5, SST, ZSim)

## Integration Interfaces

DRAMSim3 provides integration hooks for:
- **gem5**: As external memory backend
- **SST**: As memory element in SST framework
- **ZSim**: As memory timing model

## Performance Data (from Ramulator 2.0 comparison)

Simulation speed for 5M memory requests (read-write ratio 4:1):
- Random access: 51–52 ms
- Streaming access: 37–38 ms

(Comparable to Ramulator 2.0: 58–62 ms random, 31–33 ms streaming)

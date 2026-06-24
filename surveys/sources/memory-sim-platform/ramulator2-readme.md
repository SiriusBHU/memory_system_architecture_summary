# Ramulator 2.0: DRAM Simulator — README (fetched from GitHub)

> Source: https://github.com/CMU-SAFARI/ramulator2

## Project Description

Ramulator 2.0 is a successor to Ramulator 1.0, designed as "a modern, modular, and extensible cycle-accurate DRAM simulator." The tool enables researchers to rapidly prototype and evaluate innovations in memory controller design and DRAM architecture while maintaining both simulation speed and ease of extension.

## Supported DRAM Standards

- **Standard DRAM**: DDR3, DDR4, DDR5
- **Low-Power**: LPDDR5
- **Graphics Memory**: GDDR6
- **High-Bandwidth**: HBM(2), HBM3

## Key Architectural Principles

Ramulator 2.0 employs a distinctive design pattern separating interfaces from implementations:

- **Interfaces** define abstract high-level functionality as C++ classes with virtual functions
- **Implementations** provide concrete realizations inheriting from both interface classes and an `Implementation` base class
- A self-registering factory automatically constructs appropriate objects based on YAML configuration names

This decoupling enables adding new features "without intrusive changes" to existing code.

## RowHammer Mitigation Techniques

The simulator implements eight mitigation strategies:
PARA, TWiCe, Graphene, BlockHammer, Hydra, Randomized Row Swap, AQUA, and an Oracle Refresh approach.

## Build Requirements

- **Compiler**: C++20-capable (verified with g++-12, clang++-15)
- **External Libraries**: argparse, spdlog, yaml-cpp (automatically downloaded by CMake)

## Integration with gem5

Ramulator 2.0 integrates as a library into the gem5 simulator by:

1. Cloning into `gem5/ext/ramulator2/`
2. Creating an SConscript configuration file linking the library
3. Wrapping Ramulator2 as a gem5 SimObject
4. Instantiating the frontend and memory system through the factory pattern

## Configuration System

The simulator uses human-readable YAML configuration files supporting:
- Direct file specification via `-f` flag
- String-based configuration for parameter sweeping
- Python automation enabling easy experiment batching

## Performance Validation

The repository includes:
- Verilog verification against Micron DDR4 models to ensure command correctness
- Comparative performance benchmarks against DRAMSim2, DRAMSim3, USIMM, and Ramulator 1.0
- RowHammer mitigation evaluation across SPEC 2006/2017 workloads

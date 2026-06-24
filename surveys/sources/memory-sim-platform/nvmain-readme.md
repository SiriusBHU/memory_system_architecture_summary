# NVMain: Non-Volatile Memory Simulator — README (fetched from GitHub)

> Source: https://github.com/OMA-NVM/nv-NVmain

## Project Description

NVMain is an architectural-level simulator designed to evaluate emerging non-volatile memory technologies. It is a "cycle accurate main memory simulator designed to simulate emerging non-volatile memories at the architectural level."

## Supported NVM Technologies

NVMain supports simulating various NVM types including PCM, STT-RAM, ReRAM with flexible configuration for "various different variations of memory controllers, interconnects, organizations, etc."

NVMain 2.0 extended support to:
- Die-stacked DRAM caches
- Non-volatile memories (STT-RAM, PCRAM, ReRAM) including multi-level cells (MLC)
- Hybrid NVM + DRAM memory systems

## Architecture Components

NVMain includes modular components organized in separate directories:

- **Memory Control**: Custom controller implementations
- **Interconnect**: Data path configurations
- **Address Translation** (Decoders): Address mapping schemes
- **Endurance Models**: Device degradation simulation
- **Fault Models**: Hard-fault implementation
- **Prefetchers**: Cache optimization mechanisms

## gem5 Integration

The simulator supports integration with gem5 through patches. Users apply patches via git or mercurial depending on their gem5 version, then invoke simulations using the `--mem-type=NVMainMemory` parameter with a configuration file specified via `--nvmain-config`.

## Simulation Modes

NVMain operates in two configurations:

1. **Standalone trace-based**: Processes pre-recorded memory request traces using `./nvmain CONFIG_FILE TRACE_FILE`
2. **Simulator-integrated**: Patches into gem5 or other simulators for full-system evaluation

## Key Features (NVMain 2.0)

- Sub-array-level parallelism
- Fine-grained refresh modeling
- MLC and data encoder modeling
- Distributed energy profiling
- Flexible user interface with fast simulation speed

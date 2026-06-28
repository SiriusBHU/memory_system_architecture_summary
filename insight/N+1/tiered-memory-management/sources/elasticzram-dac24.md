# ElasticZRAM (DAC'24) + Ariadne (FAST'25) — local source notes

Two closely-related mobile compressed-swap papers. ElasticZRAM is the headline DAC'24
result; Ariadne (CMU-SAFARI) is read directly for richer zram numbers.

## ElasticZRAM: Revisiting ZRAM for Swapping on Mobile Devices
- **Authors:** Wentong Li, Dingcui Yu, Yunpeng Song, Liang Shi (East China Normal Univ.)
- **Venue/Year:** 61st ACM/IEEE Design Automation Conference (DAC '24), Nov 2024
- **URL:** https://dl.acm.org/doi/10.1145/3649329.3655943
- **Problem:** mobile two-level swap = ZRAM (compressed RAM) + NAND flash. ZRAM improves
  responsiveness and cuts flash write traffic, but **consumes physical memory** and burns
  **extra CPU cycles**; its sizing is static and unaware of app / flash characteristics.
- **Idea:** make ZRAM *elastic* — size it with awareness of app behavior and NAND flash,
  rebalancing the compressed-RAM tier vs the flash-swap tier at runtime.
- **Result:** on **Google Pixel 6**, improves application response time **up to 24.8%**
  with negligible overhead vs state-of-the-art.

## Ariadne: Hotness-Aware, Size-Adaptive Compressed Swap (read locally)
- **Authors:** Yu Liang, Aofeng Shen, Chun Jason Xue, Riwei Pan, Haiyu Mao, Nika Mansouri
  Ghiasi, Qingcai Jiang, Rakesh Nadig, Lei Li, Rachata Ausavarungnirun, Mohammad
  Sadrosadati, Onur Mutlu (ETH Zürich / MBZUAI / CityU HK / KCL / USTC).
- **Venue/Year:** arXiv:2502.12826, Feb 2025 (FAST'25 line of work). Code: CMU-SAFARI/Ariadne.
- **Device:** Google Pixel 7, Android 14, 30+ concurrent-app combinations.
- **Three observations:**
  1. anonymous data has different hotness; hot data is similar across relaunches.
  2. small-size compression is fast; large-size compression gives better ratio.
  3. there is locality in zpool access during relaunch (predictable next set).
- **Three techniques:** (1) low-overhead hotness-aware data organization separating hot/cold
  anon data; (2) size-adaptive compression chunk size by hotness (small=fast decompress for
  hot/warm, large=high ratio for cold); (3) proactive predictive decompression of the next set.
- **Headline numbers (avg):**
  - **Application relaunch latency: −50%** vs state-of-the-art compressed swap.
  - **Compression/decompression CPU usage: −15%.**
- **Background facts quoted:** process creation accounts for **94%** of total cold-launch
  latency; keeping apps alive in compressed RAM converts cold launches into hot launches;
  ZRAM decompression is much faster than swapping in from NAND flash.

## Why it matters for terminal tiering
These are the on-device evidence that the **DRAM ↔ compressed-RAM (zram)** tier boundary
is real, that compression ratio (~2:1 to ~3:1) and CPU cost are the live tradeoffs, and that
hotness-awareness at the swap layer (not just the LRU) yields measurable user-visible wins.

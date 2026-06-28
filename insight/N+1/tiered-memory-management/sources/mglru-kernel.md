# MGLRU (Multi-Gen LRU) — local source notes

- **Title:** Multi-Gen LRU (Linux kernel admin guide) + Google fleet results
- **Author:** Yu Zhao (Google) et al.
- **Year:** merged Linux v6.1 (2022); default on Android 14+ (2023)
- **URLs:**
  - Kernel doc: https://docs.kernel.org/admin-guide/mm/multigen_lru.html
  - Esper writeup: https://www.esper.io/blog/android-dessert-bites-22-linux-memory-management-38419756

## Mechanism
- Replaces the classic two-list **active/inactive** LRU with **multiple generations**.
  `max_gen_nr` = hottest / most-recently-accessed; `min_gen_nr` = coldest.
- **Aging:** each generation tracks the number of pages accessed within `age_in_ms`.
  Aggressively clears PTE **accessed bits in large batches** (set by MMU), in both leaf
  and non-leaf page-table entries.
- **Eviction:** cold generations (`<= min_gen_nr`) evicted proactively; the two newest
  generations are treated like the old "active list" and are not evictable.
- Enables proactive reclaim + working-set estimation; designed for memory-pressure
  responsiveness on clients (ChromeOS/Android), not servers.

## Key numbers (Google fleet, pre-upstream validation)
- Tested on **tens of millions of ChromeOS** devices and **~1 million Android** devices.
- **kswapd CPU usage: −40%** across the ChromeOS fleet.
- **Low-memory kills: −85% at the 75th percentile** (ChromeOS).
- **App launch time: −18% faster at the 50th percentile** (Android).
- Android 13 introduced MGLRU as an option; Android 14 enables it by default.

## Role in terminal tiering
MGLRU is the **hot/cold placement engine** that decides which anonymous pages get
demoted into the compressed (zram) tier and which file pages get dropped. It is the
on-device equivalent of "access-aware tiering": finer generation granularity =
better cold-page selection = fewer wrong demotions and fewer kills.

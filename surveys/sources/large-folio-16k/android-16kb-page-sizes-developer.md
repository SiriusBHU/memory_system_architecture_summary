# Support 16 KB page sizes (Android Developers)

来源 URL: https://developer.android.com/guide/practices/page-sizes
抓取日期: 2026-06-25（WebFetch 抽取的正文，非原始 HTML）
机构: Google / Android Developers
类型: 官方厂商文档

## 性能基准（Google 官方在 16KB 设备上的实测，相对 4KB）

- **应用启动时延（内存压力下）**：平均降低 **3.16%**，部分被测应用最高可达 **30%**。
  > "Lower app launch times while the system is under memory pressure: 3.16% lower on average, with more significant improvements (up to 30%) for some apps that we tested"
- **应用启动功耗**：平均降低 **4.56%**。
  > "Reduced power draw during app launch: 4.56% reduction on average"
- **相机启动**：热启动平均快 **4.48%**，冷启动平均快 **6.60%**。
  > "Faster camera launch: 4.48% faster hot starts on average, and 6.60% faster cold starts on average"
- **系统启动时间**：平均改善 **8%（约 950 毫秒）**。
  > "Improved system boot time: improved by 8% (approximately 950 milliseconds) on average"

## 内存代价（诚实的成本）

> "Devices configured with 16 KB page sizes use slightly more memory on average, but also gain various performance improvements for both the system and apps"

- 若 app 不解压 native 库（extractNativeLibs=false），16KB ELF 对齐后二进制略增大；Android 15 包管理器优化抵消了运行时成本。

## 兼容性要求

- 共享库 ELF 段必须按 **16 KB（2^14 = 16384 字节）** 对齐。
  - 验证：`llvm-objdump -p SHARED_OBJECT_FILE.so | grep LOAD`
- NDK r28+ 默认按 16KB 对齐；r27 及更低需链接参数：
  `-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384`

## 支持范围

- Android 15（API 35）及以上支持 16KB 页。
- 自 2025-11-01 起，提交 Google Play 且面向 Android 15+ 的新 app/更新必须支持 16KB 页。

注意：本页给出的是经验结果，未展开 TLB / 页表的技术原理。

# Adding 16 KB Page Size to Android (Android Developers Blog)

来源 URL: https://android-developers.googleblog.com/2024/08/adding-16-kb-page-size-to-android.html
抓取日期: 2026-06-25（WebFetch 抽取正文）
机构: Google / Android Developers Blog
年份: 2024
类型: 官方厂商博客

## 关键定量结论（最干净的单行数字）

> "an overall performance boost of 5-10% while using ~9% additional memory."

即：整体性能提升 **5–10%**，代价是约 **9%** 的额外内存占用——这是「放大粒度」的诚实代价。

## 技术原理（Google 的口径）

> "When the page size is 4 times larger, there is 4 times less bookkeeping."

页大小变 4 倍 → 记账（页表项、逐页元数据）减少到约 1/4，从而把资源从底层内存管理腾给应用。

## 实施要求

> "All applications with native code or dependencies need to be recompiled for compatibility with 16 KB page size devices."

> "All OS binaries are 16 KB aligned (-Wl,-z,max-page-size=16384)."

## 平台支持

> "Android 15 can run with 4 KB or 16 KB page sizes."

注：本博客未提及 Apple/iOS 是否已用更大页。

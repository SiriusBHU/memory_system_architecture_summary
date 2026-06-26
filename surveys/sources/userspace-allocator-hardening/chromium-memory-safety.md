# Chromium Memory Safety 统计（本地副本）

来源 URL: https://www.chromium.org/Home/chromium-security/memory-safety/
抓取方式: WebFetch（小模型抽取的 Markdown，非原始；引用以原 URL 为准）
抓取日期: 2026-06-25

---

## 关键统计

- "Around 70% of our high severity security bugs are memory unsafety problems"（约 70% 的高危安全 bug 是内存安全问题，即 C/C++ 指针错误）。
- "Half of those are use-after-free bugs."（其中**一半是 use-after-free**。）

## 分析口径

- 样本："912 high or critical severity security bugs since 2015, affecting the Stable channel."（2015 年以来稳定通道的 912 个高危/严重安全 bug。）
- 即：**约 70% × 912 ≈ 内存安全**，其中 **约 50% 是 UAF**。

## 注意（口径区分）

- 这是 **Chrome 自己的统计**：样本是 912 个高危/严重 bug，2015 起，Stable channel。
- Microsoft 的"约 70%"是**另一套统计**：Matt Miller 在 2019 BlueHat 给出的、过去约 12 年所有打了 CVE 的安全更新里约 70% 是内存安全（口径是已分配 CVE 的安全更新，不是 912 个 Chrome bug）。
- 两个 70% 数值接近但统计对象不同，**不要混为一谈**。

## 本页未含

- 没有单独给出 critical（区别于 high）的数量。
- 没有与 Microsoft 的对比数据（对比来自二手报道，如 Slashdot/ZDNet）。
- "130 critical since March 2019, 125 caused by memory corruption" 这组数字来自 Chrome 其它公开材料/媒体报道，**不在本页正文**，引用时需另找一手出处，否则标 n/a。

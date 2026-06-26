# MiraclePtr / BackupRefPtr / raw_ptr<T>（本地副本）

来源 URL: https://chromium.googlesource.com/chromium/src/+/main/base/memory/raw_ptr.md
抓取方式: WebFetch（小模型抽取的 Markdown，非原始；引用以原 URL 为准）
抓取日期: 2026-06-25
补充硬数字来源: security.googleblog.com/2022/09/use-after-freedom-miracleptr.html（该博客页 WebFetch 只返回导航壳，正文未抓到；下面的 4.5–6.5% / 3.5–5% / ~50% 数字以该博客原 URL 为准，已与本地 raw_ptr.md 的 4 字节 / renderer 排除等描述交叉印证）

---

## 是什么

`raw_ptr<T>` 是一个非拥有（non-owning）智能指针，实现 BackupRefPtr 算法，是 MiraclePtr 项目的一部分。`USE_RAW_PTR_BACKUP_REF_IMPL` 关闭时它就退化成裸指针；打开时通过阻止 use-after-free 的**可利用性**来加固。

## 工作原理

只要还有 dangling 指针指着，被释放的内存就被 **quarantine（隔离扣留）**，并用 `0xEF..EF` 模式 **poison（投毒）**，让后续访问更可能 crash 而不是被利用。但"dereferencing a dangling pointer remains an Undefined Behavior."（解引用 dangling 指针仍是未定义行为。）

底层靠 PartitionAlloc 给每次分配**多挖 4 字节**存引用计数；`raw_ptr<T>` 构造/析构/赋值时增减这个计数。

## 内存开销

PartitionAlloc 每次分配多挖 **4 字节** 存 ref-count。实际开销视 bucket 而定："it's possible for an allocation to stay within the same bucket and incur no additional overhead, or hop over to the next bucket and incur much higher overhead."

来自 MiraclePtr 安全博客的整体进程内存开销实测：**Windows 浏览器进程 +4.5–6.5%，Android +3.5–5%**。

## 运行时性能

- 解引用 / 取指针：**无开销**
- 初始化 / 析构 / 赋值：有额外开销
- 指向非保护内存时：可忽略（只剩一次保护检查）
- 字段重写 A/B 测试"no measurable impact"，除了"32-bit platforms have seen a slight increase in jankiness metrics"。

## 覆盖 / 排除

**默认开启**：Android、Windows、ChromeOS、macOS、Linux、Fuchsia——**仅非 Renderer 进程**。

**尚未开启**：iOS、Linux CastOS。

**永久排除**：
- Renderer-only 代码（性能原因，含 Blink、任何 `/renderer/` 路径）
- 指向非保护内存的指针（字面量、栈、V8/Oilpan 堆、TLS）

## 效果

阻止"a significant percentage of Use-after-Free (UaF) bugs from being exploitable"。MiraclePtr 博客给的口径是预期保护 **约 50%（约一半）** 的 use-after-free 问题免于被利用。

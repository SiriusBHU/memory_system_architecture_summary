https://developer.android.com/ai/gemini-nano

# Gemini Nano + Android AICore：系统级单副本共享模型 (Android 轴核心)

## 一手来源
- 官方文档: https://developer.android.com/ai/gemini-nano
  - 原文确认: "Gemini Nano runs in Android's AICore system service"，AICore 负责模型分发与更新，
    集中部署 Gemini Nano + LoRA + safety features (Figure 1)，而非每个 app 自带。
- 官方一手参数来源: Google «Gemini: A Family of Highly Capable Multimodal Models» 技术报告 (2023-12)
  - 镜像 PDF: https://assets.bwbx.io/documents/users/iqjWHBFdfxIU/r7G7RrtT6rnM/v0
  - 报告原文: Gemini Nano 含两个模型 —— **Nano-1 = 1.8B 参数**，**Nano-2 = 3.25B 参数**；
    面向低/高内存设备分级；部署时 **4-bit (int4) 量化**。

## 硬数字
- Nano-1: **1.8B params**；Nano-2: **3.25B params** (Google 官方技术报告)
- 量化: **int4 (4-bit)** 部署
- footprint 推算 (第三方/数学): 3B 级模型 int4 ≈ **1.5–2 GB** RAM (0.5 byte/param)；
  FP32 同模型需 ~12GB → int4 把权重缩到约 1/8。[footprint GB 为推算，官方未直给单变体 GB]

## 关键论点 (系统级共享 vs 每 app 各带一份) —— 原始→演进核心轴
- AICore 把 Gemini Nano **在系统内加载一次、跨多个 app 共享同一实例**：
  "loads Gemini Nano into memory once and shares that instance across multiple apps"
  "Multiple apps can use Gemini Nano without loading multiple copies into RAM"
  (来源: developer.android.com/ai/gemini-nano + Google AI Edge SDK 文档说明)
- 反例 (原始范式): 若 N 个 app 各自打包一份 ~1.5GB int4 模型，则占用 ≈ N x 1.5GB，
  在 8–12GB 手机上不可行；AICore 共享单副本把占用从 O(N) 降到 O(1)。
- 设备覆盖: Pixel 8/8a/8 Pro/9 系列、Galaxy S24 系列、Z Fold6/Flip6。

## 注意
- 单个 Nano 变体在 RAM 中的精确 GB 数 Google 未在公开官方文档直接给出 → 表格标 [未核实/推算]。
- 2026-04 AICore Developer Preview 引入 Gemma 4 (E2B/E4B)，相对上代最高快 4x、省电最高 60%
  (官方 blog 未给绝对 GB)；另有第三方称端侧 Gemma 模型 ~1.5GB [未核实]。

https://developer.android.com/ai/gemini-nano

# Android AICore + Gemini Nano（端侧共享模型架构）

## AICore 系统服务（关键架构点）
- AICore 是 Android **系统级服务**，不在单个 app 内运行
- 管理 Gemini Nano 的分发、更新、生命周期
- 利用设备硬件加速器做低延迟推理
- **所有 app 通过 API 访问同一个系统级模型实例**（系统级共享）
- 引述: "Gemini Nano runs in Android's AICore system service, which leverages device hardware to enable low inference latency and keeps the model up-to-date."

## 模型系统级共享（与 Apple/Huawei 对比的核心差异点）
- **下载一次，系统级共享**：所有 app 访问同一 Gemini Nano 实例
- 多个 app 使用 Gemini Nano 不会在 RAM 中加载多份副本，OS 智能管理内存占用
- 对 app 零磁盘/运行时内存额外开销
- AICore 后台管理下载与更新

## 模型参数（来源：Gemini 技术报告 arXiv 2312.11805，非本页）
- **Gemini Nano-1: 1.8B 参数**（低内存设备，如 Pixel 8 / 8a）
- **Gemini Nano-2: 3.25B 参数**（高内存/NPU 设备，如 Pixel 8 Pro、Pixel 9 系列、Galaxy S24 系列）
- 由更大的 Gemini 模型蒸馏而来，**4-bit 量化**部署
- Nano-2 质量显著优于 Nano-1，体积约为 Nano-1 的两倍
- 模型下载体积约 1GB（[未核实-来自二手报道]）

## ML Kit GenAI APIs（建在 AICore + Gemini Nano 之上）
- Prompt（文本/多模态生成）、Summarization、Proofreading、Rewriting、Image Description、Speech Recognition
- 链路: ML Kit GenAI APIs → AICore → Gemini Nano（端侧执行）

## 隐私（Private Compute Core）
- 请求隔离，不保留输入/输出记录
- AICore 与多数包隔离
- 无直接联网，经 Private Compute Services APK 间接路由
- 内置安全过滤

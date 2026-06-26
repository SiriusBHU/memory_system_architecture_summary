https://android-developers.googleblog.com/2025/05/on-device-gen-ai-apis-ml-kit-gemini-nano.html

# Android ML Kit GenAI APIs（第三方 app 调用端侧 Gemini Nano）

（来源：Android Developers Blog，2025-05；及后续 2025-08、2025-10 博客）

## 定位
- ML Kit on-device GenAI APIs 让第三方 app 集成 Gemini Nano 做端侧推理
- 建在 AICore + Gemini Nano 之上（系统级共享模型，无需 app 各自下载）

## 能力
- Summarization（摘要）、Proofreading（校对）、Rewriting（改写）、Image Description（图像描述）
- 硬数字：可摘要**最多 3,000 个英文单词**的文档；改写消息为更正式/随意语气；生成标题/元数据/替代图像描述

## 端侧优势
- 输入/推理/输出全程本地处理，数据不离开设备
- 无网络也可用，无云端费用

## 2025 进展
- 2025-08: 最新 Gemini Nano（最强多模态端侧模型）随 Pixel 10 系列发布，经 ML Kit GenAI APIs 开放
- 2025-10: ML Kit GenAI **Prompt API** Alpha 发布——支持自然语言/多模态自定义请求

## 设备支持
- AI Edge SDK 仅支持 Pixel 9 系列；
- ML Kit GenAI APIs 可用于任何支持多模态 Gemini Nano 的 Android 手机：
  HONOR Magic 7、Motorola Razr 60 Ultra、OnePlus 13、Samsung Galaxy S25、Xiaomi 15 等

## 与综述关联
对应 Apple Foundation Models 框架 / HarmonyOS 端侧能力开放——三家都在 2025 把"系统级端侧模型"通过 SDK 开放给第三方 app，
是 agentic OS"系统级模型即平台能力"的共同趋势。

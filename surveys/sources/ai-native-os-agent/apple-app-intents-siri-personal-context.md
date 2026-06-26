https://developer.apple.com/documentation/appintents

# Apple App Intents 框架 + 个性化语境 Siri（含延期状态）

（注：developer.apple.com 与 techradar 页面为 JS 渲染，WebFetch 仅取到导航；以下事实来自 WebSearch 结果摘要，URL 为官方文档/权威报道，标注为搜索摘要级来源）

## App Intents 框架定位
来源: https://developer.apple.com/documentation/appintents
- App Intents 是把 app 连接到 Apple Intelligence 与 Siri 的框架
- **Entity schemas**：把 app 内容贡献到 **Spotlight 语义索引 (semantic index)**，支撑"个性化语境 (personal context)"理解，并带溯源归属
- **Intent schemas**：让用户自然地对内容采取动作——无需定义特定短语，Siri 语言理解演进/扩展新语言时无需改代码
- 与 App Shortcuts、Spotlight、Shortcuts、visual intelligence 集成

## 新 Siri / 个性化语境的延期（关键时间线）
来源: https://www.techradar.com/computing/artificial-intelligence/this-is-what-really-happened-with-siri-and-apple-intelligence-according-to-apple
- WWDC 2024 演示：基于语义索引的个人知识 + App Intents，可跨 Messages/Email 找到内容并据此行动
  （例: "What's that podcast that Joz sent me?"）
- 该深度个性化语境能力 **2025 年未交付**
- Apple 确认推迟到 **2026 年**

## WWDC 2025 / 2026 进展
来源: https://developer.apple.com/videos/play/wwdc2025/244/ , https://developer.apple.com/videos/play/wwdc2026/240/ , https://developer.apple.com/videos/play/wwdc2026/343/
- WWDC 2025: "Get to know App Intents"
- WWDC 2026 (6 月 9 日): **SiriKit 正式弃用通知 (deprecation notice)**
- **App Intents 2.0**（iOS 27 演进）：更丰富 entity 类型、长任务流式响应、多轮对话追问、View Annotations API（语音指令中自然引用 UI 元素）
- App Schemas：构建智能 Siri 体验

## 与综述关联
App Intents 是 Apple 的"应用向系统 agent 暴露动作/实体"机制（对应 Android AppFunctions、HarmonyOS Intents Kit）；
"个性化语境 Siri"的延期，体现了 agentic OS 落地的工程难度。

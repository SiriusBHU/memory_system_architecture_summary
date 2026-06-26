https://9to5google.com/2026/02/25/android-appfunctions-gemini/

# Android AppFunctions 取代 App Actions / App Shortcuts（演进谱系）

（来源：9to5Google 2026-02-25 对 Google 官方公告的报道）

## Google 官方定义（引述）
"AppFunctions is an Android 16 platform feature and an accompanying Jetpack library that allows apps to expose specific functions for callers, such as agent apps, to access and execute on device."

## 演进谱系
- **旧机制 App Actions / App Shortcuts**: 用 shortcuts.xml + built-in intents 把用户请求映射到 app 功能
- **新机制 AppFunctions**: 现代化、面向 agentic AI；app 声明 schema（动作 + 参数），Gemini 读取 schema 并按用户请求调用函数

## 时间线（关键日期）
- **2024 年末**: 开发启动
- **2025 年 5 月**: appfunctions Jetpack 库进入 alpha
- **Android 16 / API level 36**: `android.app.appfunctions` 进入平台框架
- **2026 年 2 月**: 完整公开细节

## 执行模型（关键差异）
- AppFunctions **端侧执行**：schema 查找在端侧，通过直接 Android API 调用进入 app
- 区别于基于无障碍 (accessibility) / 屏幕覆盖 (overlay) 的自动化——更快、更可靠、app UI 更新时不会失效
- Google 把 AppFunctions 类比为 MCP，但函数在 Android 设备本地发生

## 与综述关联
体现 Android 从"App Actions 静态意图映射"演进到"AppFunctions 动态 agent 工具调用"，
是"app-centric → agentic OS"范式转移在 Android 侧的具体落地。

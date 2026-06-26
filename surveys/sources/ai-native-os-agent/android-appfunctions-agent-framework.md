https://developer.android.com/ai/appfunctions

# Android AppFunctions（应用向系统 agent 暴露功能的框架）

## 定位
- Android 平台级 API + Jetpack 库，简化移动端 MCP 集成
- 让 Android app 充当**端侧 MCP server**，把功能贡献为"工具(tools)"，供主动特性、agent、助手（如 Google Gemini）调用
- 被描述为 "mobile equivalent of tools within the Model Context Protocol (MCP)"
- 定位为 App Actions / App Shortcuts 的后继/伴随机制——用自然语言驱动跨应用任务，替代手动 UI 导航

## 状态（关键时间点）
- 实验性预览 (experimental preview)
- **最低 Android 16+**
- 截至 **2026 年 5 月**，与 Gemini 的集成处于 private preview（仅受信任测试者）

## 架构组件
- `@AppFunction` 注解（配合 KDoc 描述）声明可暴露函数
- KSP 读取注解 + KDoc → 生成 XML schema → Android OS 索引该 schema
- `AppFunctionManager`：系统级 API，发现与执行 AppFunctions
- `AppFunctionContext`：运行时上下文
- `@AppFunctionSerializable`：返回类型/数据类序列化

## 权限
- 调用方需 `EXECUTE_APP_FUNCTIONS` 权限
- 该权限**限系统级调用方**：Gemini、OEM 助手、Google 显式授权的 app
- 调用方可包括 agents、apps、AI 助手（如 Gemini）

## 工作流
1. app 用 @AppFunction 声明函数
2. Jetpack 库生成 XML schema
3. OS 索引可用 AppFunctions
4. agent 通过 AppFunctionManager 发现函数
5. agent 根据用户 prompt 选择并执行

## 测试
- `adb shell cmd app_function list-app-functions`

## 与 MCP 对比（厂商表述）
- AppFunctions：Android OS 级、端侧本地执行、低延迟、仅限 Android
- MCP：平台无关、云端远程、网络依赖、跨平台

https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/intents-kit-intro

# HarmonyOS NEXT 意图框架 Intents Kit（应用向系统声明意图）

（注：华为官方 developer.huawei.com 文档页需 JS 渲染，WebFetch 仅取到导航；以下内容整理自官方材料的二手技术综述 CSDN https://blog.csdn.net/weixin_69135651/article/details/144105250 ，标注为二手来源）

## 定位
- Intents Kit 是 "HarmonyOS 级的意图标准体系"，框架服务
- 连接应用/元服务内的业务功能，实现**智能分发 (智慧分发)**
- 把应用功能智能分发到系统入口：**小艺对话、小艺搜索、小艺建议**
- 整合 HarmonyOS 大模型、多维设备感知等 AI 能力，捕捉用户显性/潜在意图

## 支持的意图特性类别
| 特性 | 系统入口 |
|------|---------|
| 习惯推荐 | 小艺建议、桌面卡片 |
| 事件推荐 | 小艺建议、对话搜索 |
| 技能调用-语音 | 小艺对话 |
| 本地搜索 | 小艺搜索 |

## 运行逻辑
- **意图共享 (Intent Sharing)**：app 向系统共享用户行为数据，系统学习习惯做预测推荐
- **意图调用 (Intent Invocation)**：用户与系统入口交互时，HarmonyOS 把意图任务分发给对应 app 执行
- 端云配置：本地调用 / 云端调用 / 端云结合

## 注册流程
- 在**小艺开放平台**注册意图 → 选意图类型与特性 → 配置参数 → 审核（约 3 工作日）→ 上架

## 与 Apple App Intents / Android AppFunctions 的对应关系
三家都是"应用向系统 agent/助手声明可被调用的意图/动作/函数"这一范式：
- Apple: App Intents
- Android: App Functions (+ 旧 App Actions / App Shortcuts)
- HarmonyOS: Intents Kit 意图框架（分发到小艺）

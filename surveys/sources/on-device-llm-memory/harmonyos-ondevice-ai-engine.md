https://www.mindspore.cn/lite/docs/en/r2.0/use/npu_info.html

# HarmonyOS 端侧 AI 引擎 (HarmonyOS 轴, 公开信息相对有限, 多处标注 待核实)

## 一手/官方来源
- MindSpore Lite NPU 集成文档: https://www.mindspore.cn/lite/docs/en/r2.0/use/npu_info.html
- HUAWEI Developers ML Kit / MindSpore Lite 自定义模型: 
  https://developer.huawei.com/consumer/en/doc/hiai-guides/ml-mindspore-lite-0000001055328885

## 已核实事实
- **MindSpore Lite 是 HarmonyOS 内置的轻量级 AI 引擎** ("built-in lightweight AI engine of HarmonyOS")，
  支持端侧 (device-side) 推理，覆盖通用 CPU 与 **Kirin NPU**。
- 使用 NPU 需集成 **HUAWEI HiAI DDK** (libhiai*.so)，文档引用 DDK 版本 100.510.010.010。
- Kirin NPU 支持 (来自搜索摘要，需在华为平台文档二次核对): Kirin 9000/9000E/990/985/820/810 等。

## 盘古 (Pangu) 端侧 / HarmonyOS NEXT 智能 (多为厂商发布会口径, 标 待核实)
- 2024-06-21 HDC: 华为发布 PanGu 5.0 + HarmonyOS NEXT，Harmony Intelligence 生成式 AI。
- 2025-06-30: 华为开源 openPangu，模型推理面向 **Ascend AI 加速器** 优化。
- HarmonyOS 6.0 (2025-10 beta): 异构算力编排，用于端侧模型推理的设备资源池化；
  HarmonyOS PC 集成 Pangu 与 DeepSeek 做端侧 AI。[发布会口径, 参数/footprint 未公开]

## 缺口标注 (待核实)
- 华为未公开端侧盘古具体参数量、int4 footprint(GB)、KV-cache 策略、统一内存细节等硬数字。
- 设备 NPU 走 Ascend-lite / Kirin NPU + HiAI Foundation；缺乏与 Gemini Nano / Apple 同口径的可比硬数字。
- 对照分析中，HarmonyOS 列多数单元应标 [待核实/未公开]。

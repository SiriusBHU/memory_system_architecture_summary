https://arxiv.org/abs/2403.16971

# AIOS: LLM Agent Operating System

## 元信息
- arXiv ID: **2403.16971**
- 作者: Kai Mei, Xi Zhu, Wujiang Xu, Wenyue Hua, Mingyu Jin, Zelong Li, Shuyuan Xu, Ruosong Ye, Yingqiang Ge, Yongfeng Zhang (Rutgers University)
- 版本: v1 (2024-03-25) → v5 (2025-08-12, last revised)
- 发表: 被 COLM 2025 接收 (conference paper)
- 分类: cs.OS, cs.AI, cs.CL
- 代码: GitHub 开源 (AIOS / agiresearch)

## 核心思想
将 LLM 作为 "操作系统大脑"，提出 AIOS 内核 (kernel)，把资源与 LLM 专用服务从 agent 应用中隔离出来。
内核分两层：OS Kernel（处理非 LLM 操作）与 LLM Kernel（处理 LLM 专用任务）。

## LLM Kernel 关键模块
- LLM system call interface（LLM 系统调用接口）
- Agent scheduler（代理调度器，优先级调度 agent 请求以优化 LLM 利用率）
- Context manager（上下文管理器，支持快照/恢复 LLM 生成过程）
- Memory manager（内存管理器，短期记忆）
- Storage manager（存储管理器，长期持久化）
- Tool manager（工具管理器）
- Access manager（访问控制管理器）

## 硬数字
- **2.1x** 执行加速（through kernel-level scheduling, context management, memory services；相对于无 AIOS 内核的 agent framework 部署）
- 提供 AIOS SDK，封装内核功能 API

## 与综述的关联
这是 "LLM as OS kernel / agent operating system" 学术愿景的奠基性论文，把"操作系统"从比喻变成具体设计（kernel + scheduler + context/memory manager）。

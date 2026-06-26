# 两个实际案例的结构拆解：KV Cache 管理（PagedAttention）与记忆系统（MemoryOS）

> 本文给「KV Cache 的管理」和「Agent 记忆系统」各挑一个公开、可验证、可逐层拆解的真实系统，画出架构图并拆解其内部结构。是 [on-device-kv-cache-management](on-device-kv-cache-management-CN.md)（存储/分级层）与 [on-device-agent-memory-system](on-device-agent-memory-system-CN.md)（记忆系统层）的具体落地补充。
>
> 核心洞察：两者是**同一种思想（给记忆做一个 OS）落在不同时间尺度**上的实现——PagedAttention 管「激活态 KV」（毫秒/每 token），MemoryOS 管「语义记忆」（会话/每轮）；MemOS 的 `MemCube` 正好把这两层接到一起。

---

## 案例 A — KV Cache 管理：vLLM PagedAttention

**核心思想**：把操作系统的**虚拟内存分页**搬到 KV Cache 上。传统做法给每个请求预留一整段连续显存（按 `max_len`），导致 **60–80%** 被内部碎片与过度预留浪费；PagedAttention 把 KV Cache 切成定长块、按需分配、用一张块表做「逻辑→物理」映射，浪费降到 **<4%**（仅末块半满）[vLLM]。

![vLLM PagedAttention：KV Cache 分页管理结构](assets/pagedattention-arch.svg)

*图 A. PagedAttention 的三列结构：①请求的逻辑块 → ②块表映射 → ③物理 KV 块池；底部为三大机制（按需分配 / 写时复制共享 / 自动前缀缓存）。复现脚本：[assets/pagedattention-arch.py](assets/pagedattention-arch.py)。*

### 结构逐层拆

| 结构件 | 作用 | 关键参数 |
|---|---|---|
| **KV Block** | 存固定 token 数的 K/V | 默认 16 token/块（vLLM `block_size=16`） |
| **Logical Block** | 序列视角的连续块 | 序列内严格有序 |
| **Physical Block** | 显存里的实际块 | 可非连续、可被多请求共享 |
| **Block Table** | 逻辑→物理映射 + 末块填充计数 | 每请求一张，append-only |
| **Block Manager** | 按需分配/回收物理块 | 维护空闲块池 |
| **Free Queue** | 空闲 + 可复用块池 | 双向链表，按 LRU 排序 |

### 三个关键机制

1. **按需分配** —— 只有生成到新块时才分配物理块，浪费只发生在序列**最后一块**（半满），故 <4% [vLLM]。
2. **写时复制（COW）共享** —— 并行采样 / beam search 时多序列共享同一前缀的物理块，块表指向同一物理块 + **引用计数**；某序列要写入共享块时才复制。复杂采样省内存最多 **55%**，吞吐提升最多 **2.2×** [vLLM]。
3. **自动前缀缓存（跨请求复用）** —— 结构最精巧的部分：
   - **块哈希链**：`hash = H(父块hash, 本块token, 额外id如 LoRA/图像)`；包含父块 ⇒ 只有**整条前缀都相同**时哈希才相同，天然防止「位置错位」误匹配。
   - **命中**：新请求先 `get_computed_blocks()`，对 prompt 逐块哈希查表；命中的物理块被 touch（引用计数 +1、移出空闲队列防淘汰）。
   - **淘汰**：空闲块走 **LRU 双向队列**，仅当 `refcount==0` 才可淘汰；请求结束时块**逆序**归还（含更长前缀的末块更早被淘汰，因为长前缀更难被未来命中）。

### 实测数字

| 维度 | 数值 | 来源 |
|---|---|---|
| 显存浪费 | 60–80% → <4% | [vLLM] |
| 并行采样省内存 | ≤55% | [vLLM] |
| 吞吐 vs HF Transformers | 14–24×（单序列）/ 8.5–15×（3 并行） | [vLLM] |
| 吞吐 vs HF TGI | 2.2–2.5×（单）/ 3.3–3.5×（3 并行） | [vLLM] |
| LMSYS 实测 | 最高 30×，同流量省 50% GPU | [vLLM] |

> 端侧映射：llama.cpp 的 `llama_kv_cache`（cell + seq_id 集合 + `llama_kv_cache_seq_cp` 共享前缀 + 碎片整理）是同一套思想的移动端实现，对应 MemOS 的 **activation memory** 层。

---

## 案例 B — 记忆系统：MemoryOS（EMNLP 2025 Oral）

**核心思想**：把 OS 的**分层存储 + 换页**搬到 Agent 记忆上。最小单元不是 token，而是一次完整问答（Dialogue Page）；时间尺度是会话级。LoCoMo 上 F1 **+49.11%**、BLEU-1 **+46.18%**（GPT-4o-mini）[MemoryOS]。

![MemoryOS：分层记忆系统结构](assets/memoryos-arch.svg)

*图 B. MemoryOS 的三级存储主干（STM→MTM→LPM，向下沉淀晋升）+ 右侧四模块（Storage/Updating/Retrieval/Generation）+ 检索召回与 Heat 公式。复现脚本：[assets/memoryos-arch.py](assets/memoryos-arch.py)。*

### 结构逐层拆

| 层 | 结构 | 容量 / 规则 |
|---|---|---|
| **STM 短期** | Dialogue Page = `{Q, R, T, meta_chain}` 的 FIFO 队列 | **7 页**，满则挤出最旧页 |
| **MTM 中期** | 同话题页按相似度 **θ=0.6** 聚为 Segment | **≤200 段**，每段算 Heat |
| **LPM 长期画像** | User Persona + Agent Persona | User KB 100 条 FIFO；User Traits **90 维**（3 类）；Agent Traits 100 条 FIFO |

### 四个模块 = 三条数据流

| 模块 | 职责 | 关键规则 |
|---|---|---|
| **Storage** | 三级分层组织 | STM / MTM / LPM |
| **Updating** | 写入 + 晋升 | STM→MTM：FIFO + 话题链；MTM→LPM：Heat>τ=5 段换页 |
| **Retrieval** | 三级召回 | STM 全取；MTM 两阶段（top-m=5 段 → top-k=5–10 页）；LPM 每类 top-10 |
| **Generation** | 拼装 prompt | 三级召回结果合并后喂给 LLM |

### Heat 晋升公式（决定哪些中期记忆「换页」进长期画像）

```
Heat(segment) = α·N_visit + β·L_interaction + γ·R_recency      (α = β = γ = 1)
              = 被检索次数 + 段内页数 + exp(-Δt / 1e7)
晋升条件: Heat > τ (= 5)
```

这正是 OS 里「访问频率 + 驻留量 + 新近度」决定页是否常驻的翻版——**热的记忆往上沉淀为画像，冷的随时间衰减**。

---

## 两个案例的结构同构

把两张图叠起来看，它们是**同一架构在不同层的实例**：

| 维度 | PagedAttention | MemoryOS |
|---|---|---|
| 管的对象 | 激活态 KV（注意力中间状态） | 语义记忆（事实 / 画像） |
| 最小单元 | KV Block（16 token） | Dialogue Page（一次问答） |
| 时间尺度 | 毫秒 / 每 token | 会话 / 每轮 |
| OS 类比 | 虚拟内存**分页** | 分层存储 + **换页** |
| 淘汰依据 | LRU + 引用计数 | Heat（频率+量+新近度）+ FIFO |
| 复用机制 | 前缀块哈希共享 | 话题段归并 + 画像沉淀 |

**结论**：MemOS 论文里的 `MemCube` 把这两层正式接到一起——它的 **activation memory 就是 KV Cache 层（PagedAttention 管的东西）**，**plaintext memory 就是语义记忆层（MemoryOS 管的东西）**，并定义二者间的「提升/降级」（热点明文记忆 → 注入成 KV）。所以「KV 管理」和「记忆系统」在架构上不是两件事，而是同一条记忆层级的**底层（激活/KV）**与**上层（语义/画像）**。

## 参考文献

1. **vLLM / PagedAttention** — Kwon et al., 2023. "Efficient Memory Management for Large Language Model Serving with PagedAttention." SOSP 2023. Blog: https://vllm.ai/blog/2023-06-20-vllm ；前缀缓存设计：https://docs.vllm.ai/en/latest/design/prefix_caching/
2. **MemoryOS** — Kang et al., 2025. "Memory OS of AI Agent." arXiv 2506.06326，EMNLP 2025 Oral. https://arxiv.org/abs/2506.06326 ；代码：https://github.com/BAI-LAB/MemoryOS ；本地副本：[sources/on-device-agent-memory-system/memoryos-2506.06326.md](sources/on-device-agent-memory-system/memoryos-2506.06326.md)
3. **MemOS（MemCube，统一两层）** — Li et al., 2025. "MemOS: A Memory OS for AI System." arXiv 2507.03724. https://arxiv.org/abs/2507.03724 ；本地副本：[sources/on-device-agent-memory-system/memos-2507.03724.md](sources/on-device-agent-memory-system/memos-2507.03724.md)
4. **llama.cpp KV cache（端侧映射）** — ggml-org/llama.cpp. https://github.com/ggml-org/llama.cpp

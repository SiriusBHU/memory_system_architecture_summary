https://docs.vllm.ai/en/latest/design/v1/prefix_caching.html

# vLLM Automatic Prefix Caching (APC) — 官方设计文档

- **官方文档:** https://docs.vllm.ai/en/latest/design/v1/prefix_caching.html （另见 stable: https://docs.vllm.ai/en/stable/design/prefix_caching/）
- **RFC:** https://github.com/vllm-project/vllm/issues/2614
- **类型:** 开源推理框架特性（非论文），vLLM v1 在 KV cache manager 中实现。

## 核心机制（block/page 级哈希复用）
- 以 **block（页）** 为粒度缓存 KV；每个 KVCacheBlock 满块后分配一个 **block hash**，块被淘汰时重置。
- **哈希构成** = SHA256( 上一块的 hash（parent hash） + 当前块的 token id + extra keys )。extra keys 可含 LoRA ID、多模态输入 hash、cache salt（安全隔离）。默认 SHA256，可选 xxhash / CBOR 序列化。文档原文："we hash each kv-cache block by the tokens in the block and the tokens in the prefix before the block."
- **只缓存满块**（"We only cache full blocks"），未满的部分块不可复用。
- 关键数据结构：Block Pool（预分配）、cache blocks 映射（hash→block id）、request blocks 映射（request id→block ids）、Free queue（双向链表）。

## 淘汰 / 治理策略
- **reference counting**：每块记录 ref_cnt（多少请求在用）；**ref_cnt > 0 的块不可被淘汰**，保护运行中请求。
- **LRU 淘汰**：需要新块且 free queue 耗尽时，从 free queue 头部（最久未用）淘汰；"when the head block of the free queue is cached, we have to evict the block."
- 请求结束后，其未被引用的块以逆序放回 free queue 尾部，保证高频复用的前缀块最后才被淘汰。

## 硬数字
- 官方文档以机制说明为主，**未给出统一的 TTFT/吞吐数字**（具体收益依工作负载，命中越高省 prefill 越多）；如需数字应引用具体 benchmark，本页 [未提供官方统一数字]。

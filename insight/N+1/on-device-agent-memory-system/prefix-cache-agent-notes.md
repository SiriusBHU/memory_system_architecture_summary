# 端侧 Agent 的 Prefix Cache 与记忆系统设计笔记

> 从「prefix cache 的底层原理」一路梳理到「端侧 Agent 的缓存 + 记忆系统落地」。三张图分别讲**架构**(缓存怎么组织、存哪)、**方式**(上下文怎么排、那条关键边界)、**流程**(每一轮运行时怎么走)。

---

## TL;DR

- 主流 prefix cache 一律是**精确 token 前缀匹配**(用 hash 或 radix tree 索引),没有「KV 相似度匹配」这回事——相似度匹配在原理上会破坏正确性。
- 命中率高不是因为匹配松,而是因为真实负载天然是「**一段很长、逐字节相同的静态前缀 + 一小段动态尾巴**」,且命中率是按 **token 加权**统计的。
- KV 与 token 在**位置上**严格一一对应(attention 决定),但落盘的是 `hash → KV`,**token 原文一般不存,只留一个 hash 当 key**。
- 端侧 Agent 的「system 共享 + skill 分支」缓存**完全成立**:复杂度是 `O(skill 数)`,不是 `O(会话数)`。
- 一条命脉约束:**skill prompt 之前不能有任何变量**(绝对位置 + 字节都要稳);用户的情景记忆必须排到**所有静态前缀之后**,否则 skill 分支缓存全塌。

---

## 1. Prefix cache 的本质:精确 token 前缀匹配

### 为什么不是「相似度匹配」

关键事实:**KV cache 是输入 token 序列的确定性函数**。同一个模型、同样的精度下,只要前缀 token 完全一致,算出来的 KV 就逐数值一致。所以根本不需要比「相似度」——直接比 token 就等价于比 KV,而且更便宜。

反过来,「相似但不完全相同」的 token 算出来的 KV **不能复用**。因为 attention 是 causal 的,位置 `t` 的 K/V 依赖 `0..t` 的所有 token;哪怕只差一个 token,从那个位置往后的所有 KV 都会变。用一份「差不多」的 KV 顶替,等于偷偷改了模型输入,输出就错了。所以前缀必须**逐 token 严格一致**才算命中,这是个 0/1 的事。

> 注意区分:GPTCache 那类「语义缓存」确实按相似度命中,但它缓存的是整个**回答**、按 query 的 embedding 匹配,是**有损**的,只适合 FAQ/客服。它和推理引擎里的 prefix KV cache 是两个层次的东西:前者省「整次推理」,后者省「前缀那段 prefill 的算力」且无损。

### 两种索引实现

| 路线 | 代表 | 做法 |
| --- | --- | --- |
| 链式 block hash | vLLM | KV 按固定大小 block 切分,每块算 `block_hash[i] = hash(block_hash[i-1], 本块 token, …)`,带上前一块 hash 保证只有整段前缀都相同才命中。内容寻址查表。 |
| Radix tree | SGLang(RadixAttention) | 用压缩前缀树管理所有请求的 KV,树上路径就是 token 序列。新请求沿树往下走,能走多深复用多深,配 LRU 淘汰。并发请求共享 system prompt 很自然。 |

两者思路一致:**在 token 序列这一层做精确匹配**,区别只是索引结构。

---

## 2. 主流厂商都用精确前缀匹配 + 为什么命中率还高

### 三家确认(都是精确前缀匹配)

一个能直接证明的细节:它们返回的都是 token 计数而非相似度分数——DeepSeek 给 `prompt_cache_hit_tokens / prompt_cache_miss_tokens`,OpenAI 给 `cached_tokens`。

| 厂商 | 触发 | 粒度 / 约束 | 存储与 TTL |
| --- | --- | --- | --- |
| **GPT** | 自动,prompt ≥ 1024 token | 命中以 128 token 为增量;首 1024 token 差一个字符就整体 miss | 主要在 GPU 显存,分钟级(5–10 min,可到 1h);另有 24h extended(把 KV 张量 offload 到 GPU 本地存储) |
| **Opus** | 手动打 `cache_control` breakpoint(最多 4 个),也有自动模式 | 前缀必须逐字节一致,差一个 token 就 miss、按全价计费 | 主要在显存,默认 5 min TTL(每次命中刷新),可选 1h |
| **DeepSeek** | 自动,默认对所有人开启 | 按 64 token 分块,从第 0 个 token 起严格匹配,不足一块不缓存 | **落磁盘**(分布式磁盘阵列),能存几小时到几天 |

### 为什么精确匹配还能高命中率

**一、贵的、重复的那部分天然就在前缀。** system prompt、工具定义、few-shot、各种 instruction 是逐字节一样的,且按 API 设计放在最前面;真正变的只有最后一小段用户输入。所以「精确前缀」匹配到的正好是真正一致的那段。三家文档都在教你「静态内容放前面、动态内容放后面」——整个 API 就是围着这个结构设计的。

**二(更关键)、命中率是 token 加权的,不是按请求算的。** 这是最大的困惑点。「每个新请求最后那段总不一样」——对,但那段很短:

- **多轮对话**:第 `N+1` 轮把前 `N` 轮原样包含,是严格前缀。对话越长可复用前缀越大。
- **Agent 循环**:`prompt → 调工具 → 工具返回 → 再推理`,轨迹一直往后长,每步都把之前整条轨迹当前缀。一个复杂任务能跑 20–40 次以上模型调用,每次复用越来越长的前缀。

于是一次请求里可能 5 万 token 的前缀全命中、只有最后几百 token 是新的。`命中率 = cached_tokens / prompt_tokens` 自然就是 90%+。**每个请求技术上都是「前缀命中 + 尾部 miss」,但尾部相对前缀小得可怜,token 加权后命中率就很高。**

再叠加工程放大:TTL 每次读缓存都刷新,活跃会话能一直保持温热;OpenAI 还提供 `prompt_cache_key` 等机制,把共享前缀的流量导到同一台机器(否则缓存写在 A 机、请求落到 B 机照样 miss)。

### 一句话

> 命中率高不是匹配放松了,而是真实负载被刻意设计成「长静态前缀 + 短动态尾巴」,精确匹配在这种结构下足够用,而 token 加权的指标天然就高。

---

## 3. KV 与 token 的关系:位置级一一对应 vs 内容寻址存储

把两层分开就清楚了:

**张量层面——是的,KV 和 token 位置一一对应。** 一段 `T` 个 token 的序列,KV 就是「每层 × 每个 token 位置」各存一组 K/V。位置 `t` 的 token 贡献位置 `t` 的 K/V,且因 causal 依赖 `0..t`。这个对应关系是 attention 机制决定的,改不了。

**存储与匹配层面——不是把「token → KV」原样落盘逐 token 比对。** 实际是内容寻址:把前缀切块,对每块算 hash,存 `hash(前缀块) → 该块 KV`。匹配时拿前缀块算 hash 去查表(块级 lookup),不是从头逐 token 扫。

**而且 token 本身通常根本不落盘。** 出于隐私,厂商落盘的只有 KV 张量,token 原文只化成一个 hash 当钥匙:

- Anthropic:不存 prompt 原文,KV 表示与内容 hash 只在内存。
- OpenAI:只有 K/V 张量写进本地存储,原始 prompt 文本只留内存。

> 所以严格讲不是「token 和 KV 一起完整一一落盘」,而是 **KV 落盘、token 只剩一个 hash**。

**为什么 hash 当 key 就够?** 用强 hash(类 SHA-256)碰撞概率可忽略,可以只靠 hash 命中而不存原文核对。有些实现为绝对保险会额外存一份 token id 做防碰撞校验,用密码学 hash 时很多就直接省了。

**为什么 DeepSeek 能塞进磁盘?** 普通 MHA 每个 token 位置要存所有 head 的完整 K/V,体积大;**MLA**(DeepSeek V2)把它压成低秩 latent(外加一小段 RoPE),每位置存的东西小得多,便宜到能上磁盘。它据称是全球第一个在 API 里大规模做磁盘缓存的厂商。

**一个新 wrinkle:** 带稀疏/滑窗注意力的模型(如 V3.2),位置 `t` 的 KV 不再严格依赖全部前文,缓存前缀因此变成一个个**独立完整的单元**,后续请求必须**完整匹配某个缓存前缀单元**才命中,匹配语义比纯前缀更严。属进阶细节,知道有这回事即可。

---

## 4. 匹配过程:从第 0 块到第一个 miss

标准流程:取**最长匹配前缀**,在第一个 miss 处停下,拿 `0..n-1` 这 `n` 块 KV,从第 `n` 块开始重算。

**「停在第一个 miss」不是启发式,而是必然正确的:**

1. block hash 是链式的——第 `n` 块对不上,它的 hash 就变,而第 `n+1` 块的 hash 又从第 `n` 块算出,所以后面全塌,不可能「miss 后又接回去」。
2. causal attention——第 `n` 位置往后的 KV 都依赖那个变掉的 token,就算某块 hash 侥幸撞上,那份 KV 也是错的。

所以可复用区域天然是「从 0 开始的一段连续前缀」,没有跳过中间再续上。

**「miss」有两种,都一样停在 `n` 重算:**

- **前缀分叉**:token 真的不一样。
- **缓存缺失**:token 一样,但那块 KV 被淘汰了 / 当时没持久化。实践中「该命中却没命中」很多是这种——前缀没变,只是缓存被清了。

**「取出来」看在哪一层:**

- 显存内缓存(vLLM/SGLang):不搬数据,新请求的 block table 直接指向已存在的物理块,copy-on-write 共享,**零拷贝**。
- 磁盘缓存(DeepSeek):才是字面意义地把这 `n` 块从盘 load 进 HBM。

**取完还有下半场:** 从第 `n` 块开始 prefill 把剩下算完,这些新块也会 hash 后**写回缓存**,于是下一个请求能命中更长前缀。这正是 Agent 多轮里前缀越滚越长、命中率越来越高的原因。

> 两个细节:匹配是**整块**为单位的,不满一块的尾巴不作为缓存单元;稀疏/滑窗注意力是例外(整体匹配缓存单元,而非逐块往后扫)。常规全注意力下,上面就是标准做法。

---

## 5. 端侧 Agent 的分支缓存架构

### 5.1 先打消顾虑:按 skill 数扩展,不按会话数

「用户会话千千万」指的是对话尾巴千变万化,但要缓存的根本不是尾巴。所有会话共享同一个 system prompt、再落到有限几个 skill 上——可缓存前缀树就这么大:**一个根 + N 个 skill 分支**,N 可能就几十个。会话只在 skill 之后的对话里分叉,而那段本来就不打算跨会话复用。

> 复杂度是 `O(skill 数)`,不是 `O(会话数)`,完全 tractable。

正确模型就是一棵 radix tree:

<svg width="100%" viewBox="0 0 680 360" role="img" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <title>端侧 Agent prefix cache 的管理架构</title>
  <desc>一棵前缀缓存树:系统提示词为根、各 skill 为分支,并按常驻内存与按需落盘两个存储层着色。</desc>
  <defs>
    <marker id="arrowA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#73726c" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  <rect x="200" y="40" width="240" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="320" y="61" font-size="14" font-weight="500" fill="#085041" text-anchor="middle" dominant-baseline="central">系统提示词(根)</text>
  <text x="320" y="79" font-size="12" fill="#0F6E56" text-anchor="middle" dominant-baseline="central">含清单 · 全员共享</text>
  <line x1="320" y1="96" x2="115" y2="160" stroke="#73726c" stroke-width="1.5" fill="none" marker-end="url(#arrowA)"/>
  <line x1="320" y1="96" x2="265" y2="160" stroke="#73726c" stroke-width="1.5" fill="none" marker-end="url(#arrowA)"/>
  <line x1="320" y1="96" x2="415" y2="160" stroke="#73726c" stroke-width="1.5" fill="none" marker-end="url(#arrowA)"/>
  <line x1="320" y1="96" x2="565" y2="160" stroke="#73726c" stroke-width="1.5" fill="none" marker-end="url(#arrowA)"/>
  <rect x="50" y="170" width="130" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="115" y="191" font-size="14" font-weight="500" fill="#085041" text-anchor="middle" dominant-baseline="central">skill A</text>
  <text x="115" y="209" font-size="12" fill="#0F6E56" text-anchor="middle" dominant-baseline="central">常驻内存</text>
  <rect x="200" y="170" width="130" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="265" y="191" font-size="14" font-weight="500" fill="#085041" text-anchor="middle" dominant-baseline="central">skill B</text>
  <text x="265" y="209" font-size="12" fill="#0F6E56" text-anchor="middle" dominant-baseline="central">常驻内存</text>
  <rect x="350" y="170" width="130" height="56" rx="8" fill="#FAECE7" stroke="#993C1D" stroke-width="0.5"/>
  <text x="415" y="191" font-size="14" font-weight="500" fill="#712B13" text-anchor="middle" dominant-baseline="central">skill C</text>
  <text x="415" y="209" font-size="12" fill="#993C1D" text-anchor="middle" dominant-baseline="central">按需落盘</text>
  <rect x="500" y="170" width="130" height="56" rx="8" fill="#FAECE7" stroke="#993C1D" stroke-width="0.5"/>
  <text x="565" y="191" font-size="14" font-weight="500" fill="#712B13" text-anchor="middle" dominant-baseline="central">skill D</text>
  <text x="565" y="209" font-size="12" fill="#993C1D" text-anchor="middle" dominant-baseline="central">按需落盘</text>
  <rect x="50" y="266" width="14" height="14" rx="3" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="72" y="273" font-size="12" fill="#5F5E5A" dominant-baseline="central">常驻内存:system + 热门 skill,命中零加载</text>
  <rect x="50" y="294" width="14" height="14" rx="3" fill="#FAECE7" stroke="#993C1D" stroke-width="0.5"/>
  <text x="72" y="301" font-size="12" fill="#5F5E5A" dominant-baseline="central">按需落盘:冷 skill,用到才从盘 load</text>
  <text x="50" y="329" font-size="12" fill="#5F5E5A" dominant-baseline="central">内容寻址 key = hash(模型 · 量化 · prompt 文本),prompt 改即失效</text>
</svg>

system 那段 KV 全树共用,每个 skill 的 KV 是在它之上算出来的增量。

### 5.2 端侧的「超能力」:静态且提前已知

服务端是运行时才发现前缀、被动建 hash 表;端侧不一样——system prompt 和每个 skill prompt 的文本**出厂就知道**,模型与量化又固定,所以这些 KV 是**确定性的、永久有效的**(直到改 prompt 或换模型),而且**跨 App 重启都能用**。由此得到三条落地设计:

1. **预计算 + 落盘**:system KV 首次启动算一次写盘(或当资源打包进去);各 skill KV 首次用到时算、然后写盘。之后任何会话、任何重启都从盘 load,不重算。
2. **两级常驻**:RAM 常驻 system KV + 最近/最常用的几个 skill;其余 skill KV 留盘按需 load。key 集合又小又已知,LRU 甚至手动 pin 热门 skill 都行。
3. **用 agent 的路由信号做 prefetch**:在真正调某个 skill 之前就已决定要调哪个,拿这个决定提前异步把那个 skill 的 KV load/算好,把 TTFT 藏掉。

### 5.3 内容寻址做失效

每份落盘的 KV 用 `key = hash(模型 id + 量化 + 该段 prompt 文本)`。哪天改了某个 skill 的措辞,hash 就变,旧 KV 自动被忽略,不会偷偷复用过期 KV——prompt 一迭代就靠它兜底,别省。

### 5.4 命脉约束:skill 之前不能有任何变量

这是「静态内容放前面」在端侧推到极致。原因是**位置**:大多数实现里 RoPE 在 K 存进 cache 之前就按位置烤进去了,所以一个 skill 的缓存 KV 只在它落在**完全相同的绝对位置**时才有效。只要在 skill 前面塞了时间戳、user id、动态记忆,后面所有 token 位置整体偏移,**所有 skill 分支缓存全废**。

<svg width="100%" viewBox="0 0 680 370" role="img" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <title>上下文组装与静/动态边界</title>
  <desc>上下文按 token 顺序自上而下:上方是逐字节一致、位置固定的静态可缓存区(系统提示词与选中的 skill),中间一条静与动态的边界,下方是不可缓存、不可上移的动态尾巴(用户情景记忆与当前对话)。</desc>
  <text x="45" y="30" font-size="12" fill="#5F5E5A" dominant-baseline="central">token 顺序:上 = position 0,下 = 序列末尾</text>
  <rect x="45" y="46" width="590" height="52" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="340" y="65" font-size="14" font-weight="500" fill="#085041" text-anchor="middle" dominant-baseline="central">系统提示词 + skill 清单</text>
  <text x="340" y="83" font-size="12" fill="#0F6E56" text-anchor="middle" dominant-baseline="central">全员共享 · 缓存命中</text>
  <rect x="45" y="108" width="590" height="52" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="340" y="127" font-size="14" font-weight="500" fill="#085041" text-anchor="middle" dominant-baseline="central">选中的 skill X · 完整 prompt</text>
  <text x="340" y="145" font-size="12" fill="#0F6E56" text-anchor="middle" dominant-baseline="central">按需 restore · 仍命中缓存</text>
  <rect x="45" y="172" width="590" height="52" rx="8" fill="#FCEBEB" stroke="#A32D2D" stroke-width="0.5"/>
  <text x="340" y="191" font-size="14" font-weight="500" fill="#791F1F" text-anchor="middle" dominant-baseline="central">静 / 动态边界</text>
  <text x="340" y="209" font-size="12" fill="#A32D2D" text-anchor="middle" dominant-baseline="central">线以上可缓存(位置固定 + 字节一致) · 线以下不缓存且不可上移</text>
  <rect x="45" y="236" width="590" height="52" rx="8" fill="#FAECE7" stroke="#993C1D" stroke-width="0.5"/>
  <text x="340" y="255" font-size="14" font-weight="500" fill="#712B13" text-anchor="middle" dominant-baseline="central">检索到的用户情景记忆</text>
  <text x="340" y="273" font-size="12" fill="#993C1D" text-anchor="middle" dominant-baseline="central">每用户每会话 · 必须在此线下方</text>
  <rect x="45" y="298" width="590" height="52" rx="8" fill="#FAECE7" stroke="#993C1D" stroke-width="0.5"/>
  <text x="340" y="317" font-size="14" font-weight="500" fill="#712B13" text-anchor="middle" dominant-baseline="central">当前对话历史 + 新输入</text>
  <text x="340" y="335" font-size="12" fill="#993C1D" text-anchor="middle" dominant-baseline="central">动态尾巴 · 每轮只 prefill 这段</text>
</svg>

> 规则:**从 token 0 到 skill prompt 结束这一整段,跨会话必须逐字节一致;任何按用户变的东西一律挪到 skill 之后的尾巴里。** 满足这条,字节匹配(保证 V 正确)和位置匹配(保证带 RoPE 的 K 正确)就一起拿到了。

### 5.5 两个要诚实面对的限制

- **会话中途串多个 skill**:若 skill 互斥(一会话只走一个),就是上面那棵干净的树。但若同一对话里先用 A、聊几轮、再用 B,B 的前缀是 `system + A + 对话`,不在 system 正后方,匹配不到预算分支。结论:**预计算分支只让「入口那个 skill」的 prefill 免费,中途再切的 skill 还得现算**;想缓存组合会组合爆炸,不划算。好在 **system 那段永远在 position 0、永远共享**,光这一块就够本,skill 分支是锦上添花。
- **短 skill 上 load 不一定比重算快**:读几十 MB KV + dequant 也有耗时。长且常用的 system 几乎稳赢;几百 token 的小 skill 建议实测 `(读盘 + 反量化)` vs `(直接 prefill)`,别无脑全缓存。内存紧可把 KV 量化到 Q8/Q4 塞更多分支,代价是数值略偏。

---

## 6. 路由:先判断要用哪个 skill,再去取对应 cache

### 6.1 那个「假循环」

「要跑模型才知道用哪个 skill,可 skill cache 就是为了省模型算力,岂不白省」——不矛盾,因为路由和执行碰的是不同的东西,贵的那部分根本不参与路由:

- 路由只需要看 skill 的**简短描述**(名字 + 一句话),不需要看 skill 的**完整 prompt**。
- 缓存要省的正是那段完整 prompt 的 prefill——它只在**定了 skill 之后、执行那一轮**才被加载。

> 顺序:便宜的描述 → 便宜的判断 → 知道是 skill X → restore X 的 KV → 跑执行。路由便宜,执行的 prefill 贵,缓存省的是后者,两者不打架。

### 6.2 可能压根不用路由

skill 数不多、prompt 又短时,可把 `system + 所有 skill` 拼成**一个**静态前缀全缓存,让模型一次调用里自己挑(隐式路由)。代价是每轮扛满所有 skill 的 KV 内存、模型在无关 skill 上分神。端侧内存通常否决这条,但 N 小时它最省事。

### 6.3 路由档位与运行时流程

从轻到重:① 规则/关键词(最便宜,脆);② **embedding 相似度(端侧首选)**——skill 描述 embedding 离线存好,运行时只对用户输入做一次 embedding 前向(无自回归 decode),取 top-k,通常比一次完整 LLM decode 便宜一两个数量级;③ 小分类器(更准,要维护);④ 让 agent 大模型自己选(最准、能处理含糊意图,但要一次真 decode,端侧最贵)。建议默认 ②,含糊时退到 ④。

<svg width="100%" viewBox="0 0 680 510" role="img" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <title>端侧 Agent 一轮对话的运行时流程</title>
  <desc>自上而下:用户新输入 → 轻量路由选出 top-k skill(同时异步预取候选 skill 的 KV)→ 组装上下文(system 命中、skill restore、情景记忆、对话)→ 执行只 prefill 动态尾巴并生成 → 写回缓存,使下一轮命中更长前缀。</desc>
  <defs>
    <marker id="arrowC" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#73726c" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  <rect x="160" y="40" width="280" height="44" rx="8" fill="#F1EFE8" stroke="#5F5E5A" stroke-width="0.5"/>
  <text x="300" y="62" font-size="14" font-weight="500" fill="#2C2C2A" text-anchor="middle" dominant-baseline="central">用户新一轮输入</text>
  <line x1="300" y1="84" x2="300" y2="104" stroke="#73726c" stroke-width="1.5" fill="none" marker-end="url(#arrowC)"/>
  <rect x="160" y="114" width="280" height="56" rx="8" fill="#EEEDFE" stroke="#534AB7" stroke-width="0.5"/>
  <text x="300" y="135" font-size="14" font-weight="500" fill="#3C3489" text-anchor="middle" dominant-baseline="central">路由 (embedding)</text>
  <text x="300" y="153" font-size="12" fill="#534AB7" text-anchor="middle" dominant-baseline="central">只读短描述 → 选出 top-k skill</text>
  <rect x="470" y="114" width="160" height="56" rx="8" fill="#EEEDFE" stroke="#534AB7" stroke-width="0.5"/>
  <text x="550" y="135" font-size="14" font-weight="500" fill="#3C3489" text-anchor="middle" dominant-baseline="central">异步预取</text>
  <text x="550" y="153" font-size="12" fill="#534AB7" text-anchor="middle" dominant-baseline="central">预热候选 KV</text>
  <line x1="440" y1="142" x2="462" y2="142" stroke="#73726c" stroke-width="1.5" fill="none" marker-end="url(#arrowC)"/>
  <line x1="550" y1="170" x2="450" y2="234" stroke="#73726c" stroke-width="1.5" fill="none" marker-end="url(#arrowC)"/>
  <line x1="300" y1="170" x2="300" y2="200" stroke="#73726c" stroke-width="1.5" fill="none" marker-end="url(#arrowC)"/>
  <rect x="160" y="210" width="280" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="300" y="231" font-size="14" font-weight="500" fill="#085041" text-anchor="middle" dominant-baseline="central">组装 context</text>
  <text x="300" y="249" font-size="12" fill="#0F6E56" text-anchor="middle" dominant-baseline="central">system 命中 + skill restore + 情景 + 对话</text>
  <line x1="300" y1="266" x2="300" y2="296" stroke="#73726c" stroke-width="1.5" fill="none" marker-end="url(#arrowC)"/>
  <rect x="160" y="306" width="280" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
  <text x="300" y="327" font-size="14" font-weight="500" fill="#085041" text-anchor="middle" dominant-baseline="central">执行</text>
  <text x="300" y="345" font-size="12" fill="#0F6E56" text-anchor="middle" dominant-baseline="central">只 prefill 动态尾巴 → 生成</text>
  <line x1="300" y1="362" x2="300" y2="392" stroke="#73726c" stroke-width="1.5" fill="none" marker-end="url(#arrowC)"/>
  <rect x="160" y="402" width="280" height="56" rx="8" fill="#F1EFE8" stroke="#5F5E5A" stroke-width="0.5"/>
  <text x="300" y="423" font-size="14" font-weight="500" fill="#2C2C2A" text-anchor="middle" dominant-baseline="central">写回缓存</text>
  <text x="300" y="441" font-size="12" fill="#444441" text-anchor="middle" dominant-baseline="central">新算的块 hash 后入缓存</text>
  <text x="470" y="430" font-size="12" fill="#5F5E5A" dominant-baseline="central">↻ 下轮命中更长前缀</text>
  <circle cx="165" cy="482" r="6" fill="#0F6E56"/>
  <text x="178" y="485" font-size="12" fill="#5F5E5A" dominant-baseline="central">缓存 / 执行</text>
  <circle cx="300" cy="482" r="6" fill="#534AB7"/>
  <text x="313" y="485" font-size="12" fill="#5F5E5A" dominant-baseline="central">路由 / 预取</text>
  <circle cx="440" cy="482" r="6" fill="#5F5E5A"/>
  <text x="453" y="485" font-size="12" fill="#5F5E5A" dominant-baseline="central">输入 / 写回</text>
</svg>

### 6.4 延迟隐藏

- **常驻**:RAM 永久 pin 住最常用的几个 skill 的 KV,命中热门 skill 时路由一出结果 KV 已在内存,零加载。
- **预取**:top-k 路由本来就给带分数的候选,在最终 commit 前异步把 top-1(内存够就 top-2)从盘 load 进来,**路由的决策耗时正好盖住加载耗时**;路由判错时第二候选也预热好了,等于白送一个 hedge。

> 仍要诚实:路由会判错(独立的 ML 质量问题,跟缓存无关);load vs 重算的权衡对被选中的短 skill 依旧成立。

---

## 7. skill 清单本来就在 system 里(树的修正)

skill 清单(每个 skill 的名字 + 一句话)通常**已经写在 system prompt 里**——它就是 agent 知道自己有哪些 skill 可用的方式。所以不该把「清单」单拎成一个分支节点,树更干净:

```text
[system prompt(已含 skill 清单)]   ← 根,全员共享,路由和执行都用它
   ├── [skill A 的完整 prompt]       ← 执行分支
   ├── [skill B 的完整 prompt]
   └── ...
```

好处:**路由那轮和执行那轮共享的前缀更长**(路由前缀 = 整个 system;执行前缀 = `system + 某 skill`),只需持久化 system KV(最长、最值钱)+ 各 skill 增量 KV,没有「清单 KV」这种中间产物。

但要分清两件事:

- **清单(短描述)→ 进 system**,常驻,让模型/路由器知道有哪些选项,放前面没成本。
- **每个 skill 的完整 prompt → 不能全塞进 system**,否则回到「一个大前缀扛满所有 skill」那条路。

> 边界提醒:清单进了 system、而 system 必须逐字节静态,所以**清单也得静态**——别按用户动态增删条目、或往描述里插用户数据。要做「不同用户看到不同 skill 子集」,就让那批用户走自己的 system 变体(按变体分桶,变体数别爆),或把可见性放到 system 之后控,别动 system 那段字节。

---

## 8. 这算记忆系统的一部分吗

**算,但要放进准确的那一格。** 借认知科学的三分:

| 记忆类型 | 是什么 | 性质 | 在本架构里 |
| --- | --- | --- | --- |
| **语义 / 能力记忆** | 你会做什么、知道什么(system + skill 库) | 静态、跨会话、全员共享 | **就是这套 prefix 缓存** |
| **情景记忆** | 某用户某会话发生过什么(历史、事实、偏好) | 每用户、每会话、动态 | 向量库/KV store,运行时检索后拼进 prompt |
| **工作记忆** | 此刻 context window 里正在处理的 | 临时,一轮就过 | 当前对话尾巴 |

你缓存的 skill prefix KV,是语义记忆里「能力」那部分的**预计算执行态表示**——坐在最静态、最共享的那一格。

**为什么必须强调定位:** 能力侧要的是「逐字节静态、跨会话不变」,情景侧要的恰恰相反「每用户每会话都不同、还经常更新」。这两套属性冲突,所以记忆系统这把伞下至少是两套机制:

1. **能力侧(本套)**:内容寻址静态 KV 缓存,key = `hash(模型 + 量化 + prompt 文本)`,跨会话跨重启复用。
2. **情景侧(经典记忆系统)**:每用户向量库/KV store,运行时检索再拼进 prompt。

**特别注意的陷阱(踩在第 5.4 的约束上):** 很多记忆系统是「把检索到的记忆插在 system 后、对话前」。但在本架构里,情景记忆若往前缀里塞,会把所有 token 位置整体顶偏,**精心预算的 skill 分支缓存全废**。所以:

```text
[system + skill 清单]        ← 静态,缓存命中     ✅ 能力记忆
[选中的 skill 完整 prompt]    ← 静态分支,缓存      ✅ 能力记忆
─────────────────────────────────────────────
[检索到的用户/会话记忆]       ← 动态,放这之后     ⚠️ 情景记忆,绝不能往上塞
[当前对话]                    ← 动态尾巴
```

> 结论:它是记忆系统里「能力/语义记忆」这一格的高效实现,解决的是「如何把固有能力快速装进 context」;而「如何记住这个用户」是另一块拼图(情景记忆),机制不同,且必须被严格关在所有静态前缀的下游。

---

## 附:关键约束速查

1. 前缀匹配是 **0/1 精确**的,逐 token;命中率按 **token 加权**统计,所以长前缀 + 短尾巴 = 高命中率。
2. 落盘的是 `hash → KV`,**token 原文不存**;key 里务必带上**模型 + 量化 + prompt 文本**,改任一项即失效。
3. **从 token 0 到 skill prompt 结束**必须逐字节一致 + 绝对位置固定(RoPE 烤进 K);**任何动态内容一律放到尾巴**。
4. **先路由(轻,读短描述)再取 cache(重,加载完整 prompt KV)**;用常驻 + top-k 预取把加载延迟塞进路由的决策时间。
5. 入口 skill 免费,**中途再切的 skill 仍需现算**;短 skill 要实测 `load+dequant` vs `prefill`。
6. 情景记忆与 skill 缓存是两套机制,**情景记忆必须排在所有静态前缀之后**。

---

*备注:本文内嵌的三张图是自包含 SVG(颜色写死、用 SVG 原生属性),在本地 Markdown 预览(VS Code / Obsidian / Typora)及转 HTML 时可直接渲染。GitHub 出于安全不渲染 README 里的内联 SVG;若要在 GitHub 上显示,可把三张图导出成独立 `.svg` 文件再用图片引用。*

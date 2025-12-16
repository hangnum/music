# LLM 动态播放队列管理（硅基流动）开发计划

## 目标与范围

目标：新增一个服务模块，使播放器可以通过调用 LLM（当前支持硅基流动 SiliconFlow API）根据自然语言指令动态调整播放队列。

本期范围（MVP）：
- 仅对“当前播放队列”做管理：重排 / 去重 / 截断 / 置顶等（不自动从媒体库新增曲目）。
- 提供可编程接口（Service），UI 入口后续再接入。
- 所有网络调用可被 mock，单元测试不依赖真实 API。

不在本期范围：
- 自动从媒体库按语义推荐新增曲目（需要多轮检索/工具调用协议）。
- 联网下载封面/歌词等。

## 配置与鉴权

配置位置：`config/default_config.yaml` 或 `ConfigService` 默认配置。

关键配置：
- `llm.provider`: `siliconflow`
- `llm.siliconflow.base_url`: 默认 `https://api.siliconflow.cn/v1`
- `llm.siliconflow.model`: 例如 `Qwen/Qwen2.5-7B-Instruct`
- `llm.siliconflow.api_key_env`: 默认 `SILICONFLOW_API_KEY`
- `llm.siliconflow.api_key`: 可选（不建议提交）
- `llm.queue_manager.*`: `max_items`, `temperature`, `max_tokens`, `json_mode`

推荐使用环境变量：
```bash
export SILICONFLOW_API_KEY="YOUR_KEY"
```

## 模块设计

文件：
- `src/services/llm_queue_service.py`：核心实现

核心职责：
1. 把队列快照（曲目 id/title/artist/album/duration）与用户指令拼成 prompt。
2. 调用 SiliconFlow Chat Completions API，获取严格 JSON 输出。
3. 解析为 `QueueReorderPlan`，校验 id、去重、过滤未知条目。
4. 将计划应用到 `PlayerService`：通过 `set_queue(new_queue, new_index)` 重建队列并保持当前曲目指针。

## Prompt 协议（MVP）

输入：
- `instruction`: 用户指令（自然语言）
- `current_track_id`: 当前曲目（可选）
- `queue`: 列表（每项含 `id/title/artist/album/duration_ms`）

输出（JSON，且仅 JSON）：
```json
{
  "ordered_track_ids": ["..."],
  "reason": "..."
}
```

规则：
- `ordered_track_ids` 只能包含输入队列中的 `id`；允许少于原队列（表示移除）。
- 客户端会把“未提及曲目”追加到队尾（防止意外丢歌）。
- LLM 输出为空或非法时，保持原顺序。

## 迭代步骤（建议按顺序落地）

1. **基础连通**：实现 `SiliconFlowClient`（urllib），支持超时、错误信息透出。
2. **计划生成**：实现 `suggest_reorder()`，完成 prompt、json 解析、校验与兜底策略。
3. **计划应用**：实现 `apply_reorder_plan()`，保证：
   - 当前曲目仍存在时 `current_index` 对齐；
   - 未提及曲目追加到队尾；
   - 不直接操作 `_queue` 私有字段，只使用 `set_queue()`。
4. **测试**：新增 `tests/test_llm_queue_service.py`，覆盖：
   - code fence/非 JSON 处理；
   - 过滤未知 id、去重；
   - 应用后当前曲目索引保持。
5. **接入 UI（下一期）**：在 `PlayerControls` 或菜单新增“AI 队列”入口，异步调用并显示 plan.reason。

## 验收标准

- 本地设置 `SILICONFLOW_API_KEY` 后，可通过代码调用生成并应用队列重排（不会卡 UI 线程的接入留到下一期）。
- 单元测试可在无网络环境下稳定运行（mock client）。
- LLM 输出异常不会导致崩溃：要么报错可读、要么保持原队列。

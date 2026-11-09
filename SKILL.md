---
name: multi-profile-deploy
version: 0.1.0
author: Hermes Agent
license: MIT
description: 按目标机供应商自适应部署多profile子代理审计执行体系。
metadata:
  hermes:
    tags: [Hermes, Profiles, Delegation, Deployment, Multi-Agent]
---

# 多 Profile 子代理体系部署

在任意一台 Hermes 上部署「主会话 + 职能 profile（双路审计/执行/调研/编码）」的 profile_routes 工作体系。模型分配**跟随目标机实际供应商自适应**，不写死型号；同时探测目标机 standard-workflow 版本（v2 旧版 / v3 新版）并按对应口径接线。不做模型选型之外的事：不装 gateway、不动主会话既有平台配置。

## When to Use

- 「在新 Hermes 上部署多 profile 体系」「给这台机器配审计/执行 profile」
- 「按这家供应商配一套双路审计」
- 目标机已有 provider/模型，需要 profile_routes 白名单 + 职能 profile 全套落地

## Prerequisites

- Hermes ≥ 0.22.5 + 官方插件 `advanced-delegation`（`hermes plugins info advanced-delegation` 确认 enabled）
- 至少一个已配好凭证的主供应商（`hermes config get providers` 有内容且 `.env` 有对应键）
- 审计第 1 路固定用聚鑫（provider `juxin`，gemini-3.8-flash）；目标机无 juxin 时按分配原则降级处理
- 目标机已装 standard-workflow（v2 或 v3 均可，部署时探测）

## How to Run

1. 用 `read_file`/`terminal` 完成探测（见 Procedure 第 1 步），填一张分配表
2. 把分配表写成 `allocation.json`，用 `write_file` 落盘
3. 通过 `terminal` 调 `scripts/deploy_profiles.py --allocation <path> [--apply]`（缺省 dry-run 只打印计划）
4. 按 Verification 三层验收

## Quick Reference

```bash
hermes --version                                    # 需 ≥0.22.5
hermes plugins info advanced-delegation             # 插件状态
hermes config get model && hermes config get providers
hermes profile create <name> --description "<契约句>"
hermes delegation config --show                     # 路由白名单
hermes -p <name> chat -q "只回复 OK"                 # 单 profile 冒烟
python scripts/deploy_profiles.py --allocation a.json --apply
```

## 模型分配原则（用户拍板，跨机通用）

| 角色 | 取自 | 规则 |
|---|---|---|
| default / builder / researcher / coder | 主供应商 P | P 的 **Flash 级**模型（能力与经济性兼顾）；四 profile 同模型，隔离靠 SOUL/skill 不靠换模型 |
| auditor-deep（审计第 2 路） | 同供应商 P | P 的**最高能力模型**（通常为满血版/无 flash 后缀，如 glm-5.3 对 glm-5.3-flash）；成本高，只跑审计 |
| auditor（审计第 1 路） | **固定聚鑫 juxin / gemini-3.8-flash** | 跨供应商：其余 agent 全在 P 上，审计路放外面既保独立性又**避免同供应商并发互抢** |

探测方法：主供应商候选模型从其 `/models` 端点或 `hermes model` 选择器拿真实 id（flash/mini/air 后缀 = flash 级；无后缀/plus/pro/max = 高能力级），**先 curl chat 实测 200 再写入分配表**。无 juxin 的机器：审计第 1 路改用任一**与 P 不同源**的可用 provider 并在报告标注；完全无第二供应商 = 无法满足独立性，停下问用户。

## Procedure

1. **探测（只读）**：`hermes --version`；`hermes plugins info advanced-delegation`；`hermes config get model`、`hermes config get providers`、主供应商 `GET {base_url}/models`；探测 standard-workflow 版本：`grep '^version:' <skills根>/software-development/standard-workflow/SKILL.md`（v3.x 另有特征节 `第 -1 步：能力体检`；v2 为 1.0.0 四步门禁版）。接线差异见 `skill_view` → `references/workflow-v2-v3-wiring.md`。
2. **填分配表**：按上面原则定 `{main_provider, main_model, deep_model, audit_provider, audit_model, key_env}`；每个模型 curl 实测可用后写 `allocation.json`。
3. **dry-run**：`terminal` 跑 `scripts/deploy_profiles.py --allocation a.json`，核对将创建的 5 profile + 路由计划。
4. **应用**：加 `--apply`。脚本自动：备份 default config.yaml → `hermes profile create`（带契约 description，不用 --clone）→ 逐 profile 写 model/providers 块/.env 键/SOUL.md（模板见 `templates/souls.md`）→ Python yaml 直写路由白名单 + 回读断言。
5. **skills 挂载**：bundled 官方件自动同步无需操作；用户自装件（如 `qa-test-agent`、`standard-workflow`）用 junction 挂进 auditor/auditor-deep（Windows `cmd /c mklink /J`，POSIX `ln -s`），镜像 category 层级。builder 不挂。
6. **验收**：见 Verification。
7. **生效**：改完路由后当前会话没有 `profile` 参数——发 `/delegation profiles --now` 或 `/new`；新会话自动生效。
8. **主会话钉路由铁则（可选但推荐）**：路由描述只是语义信号，要新会话开局即确定性派发，需在 default 的 `SOUL.md` 加「Profile 派发铁则」节（6 条：门禁双路必派+prompt 注入视角 / builder-coder 边界判据 / researcher 并发上限 / 复审单双路口径 / 点名直派 / kanban 禁派）。坑见 Pitfalls 最后三条。

## Pitfalls

- **profile 不继承 default 的 providers 块与 .env 键**——缺任一运行期才报认证失败；脚本强制写入并回读断言。
- **`hermes config set` 传列表值会静默字符串化**——路由必须 Python yaml 直写 + `isinstance(list)` 断言，禁 CLI 传 JSON list。
- **`profile create` 会复制当前 model 块**（含陈旧 base_url/api_mode）——换 provider 后必须清 `model.base_url`。
- **路由名必须真实存在**（`hermes profile list` 可见）；白名单外的名字派不出去。
- **kanban 托管 worker 内不能用 profile 路由**（上游 #143662）——跨 profile 派发只从主会话发起；gateway 群聊里 approval mode 会串（#143399）。
- **`skills list` 表格超宽截断 skill 名**（`test-driven-developme…`）——grep 全名会误判不存在。
- **模型 id 在 `/models` 里存在 ≠ 能按默认参数调用**——有的模型强制思考（如 glm-5.3-flashx-legal 拒绝关闭思考，HTTP 400），选型必须实测 chat。
- v3 规范禁止把具体模型名写进 L0/L1 通用层——模型分配只进 profile 配置与 L2 适配包，模板一律用占位符。
- **改主会话 SOUL.md 用 `patch` 不用 `write_file`**——write_file 的 read-before-write 守卫会把正常 read_file 判为「partial view」拒绝整文件覆盖；用唯一锚点的 patch 定向编辑永不被拒。
- **SOUL 追加内容前先 `wc -c` 量现值，验收线写实测值**——中文 UTF-8 ≈3 字节/字，目测估算常差数倍，会撞碎自己写的验收线；文件已超预算（如 >2000 字）时须同步瘦身对冲，净增≈0。
- **SOUL 生效链路**：每轮 prompt 从盘现读，新会话自动生效；存续会话需 `hermes sessions refresh-prompts`；子代理系统提示明确排除 SOUL（identity belongs to the parent），往主 SOUL 钉路由不会污染子代理。

## Verification

三层缺一不可：

1. `hermes profile list` 显示 default + 5 个新 profile；`hermes delegation config --show` 列出 5 条路由。
2. 每 profile 冒烟：`hermes -p <n> chat -q "只回复 OK"`，看该 profile `logs/agent.log` 的 `API call #1: model=` 是否等于分配表值。
3. 端到端绑定：新会话派 `delegate_task(tasks=[{goal:"只回复收到", profile:"auditor"},{goal:"只回复收到", profile:"auditor-deep"}])`，结果 `route` 字段的 backend/label/provider/model 与分配表一致——路由生效的唯一硬证据。

## References

| 文件 | 载入时机 |
|---|---|
| `references/workflow-v2-v3-wiring.md` | 目标机 standard-workflow 是 v3（或需确认接线差异）时 |
| `templates/souls.md` | 部署时取 5 个角色的 SOUL 契约文本 |
| `scripts/deploy_profiles.py` | 通过 `terminal` 调用执行部署 |

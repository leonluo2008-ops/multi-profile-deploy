# standard-workflow v2 / v3 接线差异

部署前先探测目标机版本：`grep '^version:' <skills根>/software-development/standard-workflow/SKILL.md`；v3.x 另有唯一特征节 `## 第 -1 步：能力体检`。

## 两版共同点（profile 设计不变）

- 四步门禁：梳理需求 → 方案 → 双路独立审计 → 实施；双路并行、互不相通。
- 自己写的方案自己不能审；审计模型 ≠ 主模型。
- 角色集同名同契约：auditor / auditor-deep / builder / researcher / coder。

## v2（1.0.0，旧版）接线

- 审计模型由工作流自身指定（zbook 实践：juxin/gemini-3.8-flash）。
- 双路 = auditor + auditor-deep，派发词注明：第 2 路与主模型同族，只做深度、不承担独立性担保；两路冲突交用户裁决。

## v3（3.x，新版）差异 —— MUST 遵守

来源：gitee.com/luo-xiansen2023/stand-workflow（SPEC.md 为规范权威，v3.6.0）。

- **Tier A 双路必须不同 provider**：本体系天然满足（auditor=juxin，auditor-deep=主供应商 P）。目标机无第二供应商时无法达 Tier A，如实降级并标 `AUDIT=degraded`，不伪装达标。
- **审计模型禁止静默自动选择**（SPEC §5）：profile 配置即「显式配置」，满足协议检测；部署报告 MUST 声明双路所用模型，并提醒用户 L2 适配包的 `{{AUDIT_API_BASE}}` / `{{AUDIT_KEY_ENV}}` 填 juxin 端点与键名（与 auditor profile 一致）。
- **L0/L1 禁止写死模型名**（SPEC §5 第 5 条）：路由 description、SOUL 模板全用角色描述；模型分配只存在于 profile config 与 L2 适配包。
- **Tier B/C 降级路径**：无子代理委派的机器装不了本体系（需 Tier A），如实告知。
- **canonical 原则**：目标机是 v2 且要升 v3 时，按 stand-workflow 包 README 的 A3-A5 流程（冲突检测 → 整目录备份 → 隔离验证 → 原子替换 → 机器校验）；先升流程再部署 profile，两件事分开验收。

## 接线产物对照

| 项 | v2 | v3 |
|---|---|---|
| 双路审计触发 | 每次必跑 | Tier A 每次必跑；Tier B 降级标 `AUDIT=degraded` |
| 审计模型声明位置 | 派发词 | profile 配置 + L2 占位符 + 报告声明 |
| 模型名出现在流程层 | 允许 | 禁止，只进 profile/L2 |
| 冲突处置 | 交用户裁决 | 同 |

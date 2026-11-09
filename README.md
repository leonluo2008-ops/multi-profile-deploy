# multi-profile-deploy

Hermes Agent skill：在任意一台 Hermes 上部署「主会话 + 5 职能 profile（双路审计/执行/调研/编码）」的 profile_routes 子代理体系。

- 模型分配跟随**目标机实际供应商自适应**，不写死型号：
  - default / builder / researcher / coder → 主供应商 Flash 级模型
  - auditor-deep（审计第 2 路）→ 同供应商最高能力模型
  - auditor（审计第 1 路）→ 固定聚鑫 gemini-3.8-flash（跨源：独立性担保 + 避免同供应商并发互抢）
- 自动探测目标机 standard-workflow 版本（v2 / v3）并按对应口径接线。

## 安装

```bash
git clone https://github.com/leonluo2008-ops/multi-profile-deploy.git
cp -r multi-profile-deploy ~/.hermes/skills/devops/multi-profile-deploy
hermes skills list | grep multi-profile-deploy
```

## 快速用法

```bash
# 1. 探测目标机（providers / 插件 / workflow 版本），填分配表
# 2. dry-run
python scripts/deploy_profiles.py --allocation allocation.json
# 3. 应用
python scripts/deploy_profiles.py --allocation allocation.json --apply
```

细节、坑与验收三层：见 [SKILL.md](SKILL.md)。

## 维护

- 直接改本仓 + skill 目录同步（skill 目录即本仓检出）。
- 改完跑一遍 SKILL.md §Verification 三层验收再推。

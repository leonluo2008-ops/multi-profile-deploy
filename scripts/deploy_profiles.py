#!/usr/bin/env python3
"""multi-profile-deploy: 在目标 Hermes 上部署 5 职能 profile + profile_routes 白名单。

用法（通过 terminal 工具调用）：
  python deploy_profiles.py --allocation allocation.json           # dry-run
  python deploy_profiles.py --allocation allocation.json --apply   # 实际执行

allocation.json 格式：
{
  "main_provider": "glm-coding-plan-lite",   // 主供应商（providers 块名）
  "main_model": "glm-5.3-flash",             // Flash 级主模型
  "deep_model": "glm-5.3",                   // 同供应商最高能力模型（审计第2路）
  "audit_provider": "juxin",                  // 审计第1路供应商（跨源）
  "audit_model": "gemini-3.8-flash"
}

仅用 Python 标准库。跑前确保 hermes CLI 在 PATH。"""
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("需要 PyYAML：用目标机 Hermes 自带 venv 的 python 运行本脚本")

ROLES = ["auditor", "auditor-deep", "builder", "researcher", "coder"]
WORKERS = ["builder", "researcher", "coder"]
ROUTE_DESC = {
    "auditor": "审计第1路：对抗式审查方案与代码，只审不改，独立性担保。",
    "auditor-deep": "审计第2路：深度推理审查，与 auditor 并行、视角独立。",
    "builder": "原子执行子代理：小步改代码、跑验证命令、回报证据。",
    "researcher": "调研子代理：web 检索与一手资料取证，产出带引用的调研稿。",
    "coder": "项目级开发子代理：多文件特性实现、重构、系统性 debug，TDD + worktree。",
}
ROLE_DESC_CREATE = {
    "auditor": "独立审计子代理：对抗式审查方案与代码，只审不改。",
    "auditor-deep": "审计第2路：深度推理审查，与 auditor 并行、视角独立，只审不改。",
    "builder": "原子执行子代理：小步改代码、跑验证命令、回报证据。",
    "researcher": "调研子代理：web 检索与一手资料取证，产出带引用的调研稿。",
    "coder": "项目级开发子代理：多文件特性实现、重构、系统性 debug，TDD + worktree。",
}


def hermes_home():
    return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")


def parse_souls(skill_dir: Path):
    """从本 skill 的 templates/souls.md 解析各角色 SOUL 文本（按 ## 标题 + 围栏块）。"""
    tpl = skill_dir / "templates" / "souls.md"
    text = tpl.read_text(encoding="utf-8")
    souls, role, in_block, buf = {}, None, False, []
    for line in text.splitlines():
        if line.startswith("## ") and line[3:].strip() in ROLES:
            role = line[3:].strip()
        elif line.strip() == "```" and role:
            if in_block:
                souls[role] = "\n".join(buf).strip()
                in_block, buf, role = False, [], None
            else:
                in_block = True
        elif in_block:
            buf.append(line)
    missing = [r for r in ROLES if r not in souls]
    assert not missing, f"templates/souls.md 缺角色块：{missing}"
    return souls


def load_env(home: Path):
    vals = {}
    p = home / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allocation", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    home = hermes_home()
    alloc = json.loads(Path(args.allocation).read_text(encoding="utf-8"))
    cfg_path = home / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    providers = cfg.get("providers") or {}
    env = load_env(home)
    skill_dir = Path(__file__).resolve().parent.parent

    main_p, audit_p = alloc["main_provider"], alloc["audit_provider"]
    for p in (main_p, audit_p):
        assert p in providers, f"providers 块缺 {p}；先在 default 配好该供应商"
    for p in (main_p, audit_p):
        ke = providers[p].get("key_env")
        if ke:
            assert ke in env, f".env 缺 {ke}（{p} 的键）"

    plan = {
        "auditor": (audit_p, alloc["audit_model"]),
        "auditor-deep": (main_p, alloc["deep_model"]),
        "builder": (main_p, alloc["main_model"]),
        "researcher": (main_p, alloc["main_model"]),
        "coder": (main_p, alloc["main_model"]),
    }
    print("=== 计划 ===")
    for r in ROLES:
        print(f"  {r:14s} {plan[r][0]}/{plan[r][1]}")
    if not args.apply:
        print("dry-run 结束；加 --apply 执行")
        return

    # 1) 备份 default config
    bak = cfg_path.with_name(f"config.yaml.bak.multi-profile-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(cfg_path, bak)
    print("backup ->", bak.name)

    # 2) 建 profile（已存在则跳过）
    for r in ROLES:
        if not (home / "profiles" / r).exists():
            subprocess.run(["hermes", "profile", "create", r,
                            "--description", ROLE_DESC_CREATE[r]], check=True,
                           capture_output=True, text=True)
            print("created", r)

    # 3) 逐 profile 写配置
    souls = parse_souls(skill_dir)
    for r in ROLES:
        ph = home / "profiles" / r
        prov, model = plan[r]
        cp = ph / "config.yaml"
        c = yaml.safe_load(cp.read_text(encoding="utf-8")) or {}
        c.setdefault("providers", {})[prov] = providers[prov]
        m = c.setdefault("model", {})
        m["default"], m["provider"] = model, prov
        for stale in ("base_url", "api_mode", "key_env", "api_key"):
            m.pop(stale, None)
        cp.write_text(yaml.safe_dump(c, allow_unicode=True, sort_keys=False), encoding="utf-8")

        ep = ph / ".env"
        have = {}
        if ep.exists():
            for line in ep.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    have[k.strip()] = v.strip()
        for p in {prov, audit_p}:  # vision 指向 juxin，统一带上审计键
            ke = providers[p].get("key_env")
            if ke:
                have[ke] = env[ke]
        ep.write_text("".join(f"{k}={v}\n" for k, v in have.items()), encoding="utf-8")

        if r in souls:
            (ph / "SOUL.md").write_text(souls[r], encoding="utf-8")

        back = yaml.safe_load(cp.read_text(encoding="utf-8"))
        assert back["model"]["default"] == model and back["model"]["provider"] == prov
        assert prov in back["providers"] and "base_url" not in back["model"]
        print(f"configured {r:14s} {prov}/{model} env_keys={sorted(have)}")

    # 4) 路由白名单（Python 直写，禁 CLI 列表）
    d = cfg.setdefault("delegation", {})
    d["backend"] = "profile_routes"
    pr = d.setdefault("backends", {}).setdefault("profile_routes", {})
    pr["profiles"] = [{"name": r, "description": ROUTE_DESC[r]} for r in ROLES]
    pr["default"] = "builder"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    backc = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    got = backc["delegation"]["backends"]["profile_routes"]["profiles"]
    assert isinstance(got, list) and all(isinstance(x, dict) for x in got), "路由被写成字符串！"
    assert [x["name"] for x in got] == ROLES
    print("routes OK:", [x["name"] for x in got])
    print("完成。三层验收：profile list / 每profile冒烟+agent.log model= / route 字段")
    print("生效：/delegation profiles --now 或 /new")


if __name__ == "__main__":
    main()

from pathlib import Path

import yaml


def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    _validate(cfg)
    return cfg


def _validate(cfg: dict):
    api = cfg.get("api", {})
    errs = []
    if not api.get("base_url"):
        errs.append("api.base_url 不能为空")
    if not api.get("api_key"):
        errs.append("api.api_key 不能为空")
    if not api.get("model_name"):
        errs.append("api.model_name 不能为空")
    if not api.get("prompt"):
        errs.append("api.prompt 不能为空")
    if errs:
        msg = "\n".join(errs)
        raise ValueError(f"配置校验失败:\n{msg}")

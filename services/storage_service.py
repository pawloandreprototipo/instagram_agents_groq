import json
from pathlib import Path
from loguru import logger

from models.profile import InstagramProfile
from models.post import InstagramPost


def _sanitize(obj):
    """Remove surrogates e caracteres inválidos recursivamente."""
    if isinstance(obj, str):
        return obj.encode("utf-8", errors="replace").decode("utf-8")
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(i) for i in obj]
    return obj


class StorageService:
    def __init__(self, output_path: Path):
        self._output_path = output_path
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, profile: InstagramProfile, posts: list[InstagramPost]) -> Path:
        data = _sanitize({
            "profile": profile.to_dict(),
            "posts": [p.to_dict() for p in posts],
        })
        self._output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.success(f"JSON salvo em: {self._output_path}")
        return self._output_path
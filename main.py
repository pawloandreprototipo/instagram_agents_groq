from __future__ import annotations
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from loguru import logger
from utils.logger import setup_logger
from utils.config import get_settings
from services.instagram_service import InstagramService
from services.media_service import MediaService
from services.storage_service import StorageService
from tools.instagram_tools import init_tools
from agents.orchestrator_agent import OrchestratorAgent


def bootstrap(username: str) -> None:
    setup_logger()
    settings = get_settings()
    settings.posts_dir(username).mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    instagram_service = InstagramService()
    if not instagram_service.authenticate():
        logger.error("Falha na autenticacao. Verifique usuario/senha no .env.")
        sys.exit(1)

    media_service = MediaService(posts_base_dir=settings.posts_dir(username))
    storage_service = StorageService(output_path=settings.json_output_path(username))
    init_tools(instagram_service, media_service, storage_service)
    logger.success("Bootstrap completo.")


def main(username: str, max_posts: int = 0, download_media: bool = True, force_download: bool = False) -> None:
    bootstrap(username)
    orchestrator = OrchestratorAgent()
    result = orchestrator.run(
        username=username,
        max_posts=max_posts,
        download_media=download_media,
        force_download=force_download,
    )
    logger.success(f"Pipeline concluido! JSON em: {result['output_file']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python main.py <username> [max_posts] [download_media:true|false] [force_download:true|false]")
        sys.exit(1)

    target = sys.argv[1]
    max_p = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    dl = sys.argv[3].lower() in ("true", "1", "yes") if len(sys.argv) > 3 else True
    force = sys.argv[4].lower() in ("true", "1", "yes") if len(sys.argv) > 4 else False

    main(username=target, max_posts=max_p, download_media=dl, force_download=force)

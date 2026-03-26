from __future__ import annotations
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from agents.profile_agent import ProfileAgent
from agents.scraper_agent import ScraperAgent
from agents.media_agent import MediaAgent
from models.profile import InstagramProfile
from models.post import InstagramPost

console = Console()


class OrchestratorAgent:
    def __init__(self) -> None:
        self._profile_agent = ProfileAgent()
        self._scraper_agent = ScraperAgent()
        self._media_agent = MediaAgent()

    def run(self, username: str, max_posts: int = 0, download_media: bool = True, force_download: bool = False) -> dict:
        console.print(Panel(
            f"[bold cyan]Instagram Agent System[/bold cyan]\n"
            f"Perfil alvo: [bold]@{username}[/bold]\n"
            f"Max. posts: {'todos' if max_posts == 0 else max_posts} | "
            f"Download midia: {download_media} | Force: {force_download}",
            title="Iniciando",
            border_style="cyan",
        ))

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Coletando perfil...", total=None)

            profile: InstagramProfile = self._profile_agent.run(username)
            progress.update(task, description="Perfil coletado!")

            progress.update(task, description="Coletando publicacoes...")
            posts: list[InstagramPost] = self._scraper_agent.run(username, max_posts)
            progress.update(task, description=f"{len(posts)} posts coletados!")

            if download_media:
                progress.update(task, description="Baixando midias...")
                posts = self._media_agent.run(posts, force=force_download)
                progress.update(task, description="Midias baixadas!")

            progress.update(task, description="Salvando JSON...")
            from tools.instagram_tools import _storage_service
            output_path = _storage_service.save(profile, posts)
            progress.update(task, description="JSON salvo!")

        console.print(Panel(
            f"[bold green]Coleta finalizada![/bold green]\n"
            f"Perfil: @{username}\n"
            f"Posts: {len(posts)}\n"
            f"Arquivo: {output_path}",
            title="Concluido",
            border_style="green",
        ))

        return {
            "profile": profile.to_dict(),
            "posts": [p.to_dict() for p in posts],
            "output_file": str(output_path),
        }

"""Testes para InstagramService — sessão persistente com load/dump de settings."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def make_service(tmp_path: Path):
    """Cria um InstagramService com SESSION_FILE apontando para tmp_path."""
    with patch("services.instagram_service.get_settings") as mock_settings:
        mock_settings.return_value.instagram_username = "user"
        mock_settings.return_value.instagram_password = "pass"
        from services.instagram_service import InstagramService
        svc = InstagramService(session_file=tmp_path / ".instagram_session.json")
    return svc


class TestInstagramServiceSession:

    def test_first_login_calls_login_and_dumps_settings(self, tmp_path):
        """Sem arquivo de sessão, deve fazer login e salvar a sessão."""
        with patch("services.instagram_service.get_settings") as mock_cfg, \
             patch("instagrapi.Client.login") as mock_login, \
             patch("instagrapi.Client.dump_settings") as mock_dump:
            mock_cfg.return_value.instagram_username = "user"
            mock_cfg.return_value.instagram_password = "pass"

            from services.instagram_service import InstagramService
            svc = InstagramService(session_file=tmp_path / ".instagram_session.json")
            result = svc.authenticate()

        assert result is True
        mock_login.assert_called_once_with("user", "pass")
        mock_dump.assert_called_once_with(tmp_path / ".instagram_session.json")

    def test_existing_session_loads_settings_and_skips_login(self, tmp_path):
        """Com arquivo de sessão existente, deve carregar e não chamar login."""
        session_file = tmp_path / ".instagram_session.json"
        session_file.write_text("{}")  # simula sessão salva

        with patch("services.instagram_service.get_settings") as mock_cfg, \
             patch("instagrapi.Client.load_settings") as mock_load, \
             patch("instagrapi.Client.login") as mock_login, \
             patch("instagrapi.Client.account_info"):  # evita chamada real
            mock_cfg.return_value.instagram_username = "user"
            mock_cfg.return_value.instagram_password = "pass"

            from services.instagram_service import InstagramService
            svc = InstagramService(session_file=session_file)
            result = svc.authenticate()

        assert result is True
        mock_load.assert_called_once_with(session_file)
        mock_login.assert_not_called()

    def test_failed_session_relogin_and_dumps_new_session(self, tmp_path):
        """Sessão corrompida deve fazer re-login e salvar nova sessão."""
        session_file = tmp_path / ".instagram_session.json"
        session_file.write_text("{}")

        with patch("services.instagram_service.get_settings") as mock_cfg, \
             patch("instagrapi.Client.load_settings"), \
             patch("instagrapi.Client.account_info", side_effect=Exception("sessao invalida")), \
             patch("instagrapi.Client.login") as mock_login, \
             patch("instagrapi.Client.dump_settings") as mock_dump:
            mock_cfg.return_value.instagram_username = "user"
            mock_cfg.return_value.instagram_password = "pass"

            from services.instagram_service import InstagramService
            svc = InstagramService(session_file=session_file)
            result = svc.authenticate()

        assert result is True
        mock_login.assert_called_once_with("user", "pass")
        mock_dump.assert_called_once_with(session_file)

    def test_authenticate_returns_false_on_login_failure(self, tmp_path):
        """Falha total no login deve retornar False sem lançar exceção."""
        with patch("services.instagram_service.get_settings") as mock_cfg, \
             patch("instagrapi.Client.login", side_effect=Exception("credencial invalida")):
            mock_cfg.return_value.instagram_username = "user"
            mock_cfg.return_value.instagram_password = "pass"

            from services.instagram_service import InstagramService
            svc = InstagramService(session_file=tmp_path / ".instagram_session.json")
            result = svc.authenticate()

        assert result is False

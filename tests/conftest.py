import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def no_sleep():
    """Mocka time.sleep globalmente em todos os testes — elimina delays reais."""
    with patch("time.sleep"):
        yield

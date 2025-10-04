# coding: utf-8
"""Информация о версии приложения."""

__version__ = "1.3.1"
__status__ = "Beta"  # Beta, Stable, RC

def get_version_string() -> str:
    """Получить полную строку версии."""
    return f"v{__version__} | {__status__}"

def get_window_title() -> str:
    """Получить заголовок окна."""
    return f"Speedtest NextGen by Sparki | {get_version_string()}"

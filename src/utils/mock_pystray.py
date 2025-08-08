"""
Mock для pystray модуля (system tray)
"""

from typing import Any, Callable, Optional


class MockMenuItem:
    """Mock для MenuItem"""

    def __init__(self, text, action, **kwargs):
        self.text = text
        self.action = action
        self.kwargs = kwargs


class MockMenu:
    """Mock для Menu"""

    def __init__(self, *items):
        self.items = items


class MockIcon:
    """Mock для Icon"""

    def __init__(self, name, icon, menu=None):
        self.name = name
        self.icon = icon
        self.menu = menu
        self.visible = False

    def run(self):
        """Mock run"""
        print(f"Mock: Running tray icon {self.name}")
        self.visible = True

    def stop(self):
        """Mock stop"""
        print(f"Mock: Stopping tray icon {self.name}")
        self.visible = False

    def update_menu(self):
        """Mock update_menu"""
        print("Mock: Updating tray menu")


# Экспорт классов
Icon = MockIcon
Menu = MockMenu
MenuItem = MockMenuItem

print("Mock pystray модуль загружен")

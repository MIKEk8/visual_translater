"""
Mock для keyboard модуля
"""


class MockKeyboard:
    """Mock для keyboard функций"""

    @staticmethod
    def add_hotkey(hotkey, callback):
        """Mock add_hotkey"""
        print(f"Mock: Registering hotkey {hotkey}")
        return f"mock_hotkey_{hotkey}"

    @staticmethod
    def remove_hotkey(hotkey_id):
        """Mock remove_hotkey"""
        print(f"Mock: Removing hotkey {hotkey_id}")

    @staticmethod
    def unhook_all():
        """Mock unhook_all"""
        print("Mock: Unhooking all hotkeys")

    @staticmethod
    def is_pressed(key):
        """Mock is_pressed"""
        return False

    @staticmethod
    def wait(hotkey=None):
        """Mock wait"""
        import time

        time.sleep(0.1)

    @staticmethod
    def read_hotkey():
        """Mock read_hotkey"""
        return "ctrl+shift+a"

    @staticmethod
    def get_hotkey_name(names=None):
        """Mock get_hotkey_name"""
        return "ctrl+shift+a"


# Экспорт функций как модуль
add_hotkey = MockKeyboard.add_hotkey
remove_hotkey = MockKeyboard.remove_hotkey
unhook_all = MockKeyboard.unhook_all
is_pressed = MockKeyboard.is_pressed
wait = MockKeyboard.wait
read_hotkey = MockKeyboard.read_hotkey
get_hotkey_name = MockKeyboard.get_hotkey_name

print("Mock keyboard модуль загружен")

from types import SimpleNamespace

from src.services.plugin_service import PluginService


class DummyConfigManager:
    def __init__(self):
        self._observers = []

    def add_observer(self, obs):
        self._observers.append(obs)


class DummyPlugin:
    def __init__(self, enabled=True, available=True, kind="translation"):
        self.enabled = enabled
        self._available = available
        self.initialized = False
        self.kind = kind

    def is_available(self):
        return self._available

    def validate_config(self, cfg):
        return True, []

    def initialize(self, cfg):
        self.initialized = True
        return True

    def cleanup(self):
        self.initialized = False

    # Type-specific API
    def speak(self, text, lang):
        return self.kind == "tts"

    def translate(self, text, src, dst):
        if self.kind != "translation":
            raise RuntimeError("wrong kind")
        return ("ok", 0.9)


class DummyPluginManager:
    def __init__(self):
        self.registered_plugins = {
            "p1": DummyPlugin(kind="translation"),
            "p2": DummyPlugin(enabled=False, kind="translation"),
            "tts": DummyPlugin(kind="tts"),
            "ocr": DummyPlugin(kind="ocr"),
        }
        self.plugin_configs = {}

    # used by service
    def load_plugin_config(self, path):
        return True

    def save_plugin_config(self, path):
        return True

    def load_all_plugins(self):
        return len(self.registered_plugins)

    def unregister_plugin(self, name):
        self.registered_plugins.pop(name, None)

    def get_plugins_by_type(self, t):
        # rudimentary type filter
        mapping = {
            "translation": [p for p in self.registered_plugins.values() if p.kind == "translation"],
            "tts": [p for p in self.registered_plugins.values() if p.kind == "tts"],
            "ocr": [p for p in self.registered_plugins.values() if p.kind == "ocr"],
        }
        return mapping.get(getattr(t, "value", str(t)), list(self.registered_plugins.values()))

    def get_plugin_info(self):
        return [
            {"name": k, "enabled": v.enabled, "type": v.kind}
            for k, v in self.registered_plugins.items()
        ]

    def get_plugin(self, name):
        return self.registered_plugins.get(name)

    def enable_plugin(self, name):
        p = self.get_plugin(name)
        if p:
            p.enabled = True
            return True
        return False

    def disable_plugin(self, name):
        p = self.get_plugin(name)
        if p:
            p.enabled = False
            return True
        return False


def test_initialize_and_cleanup(monkeypatch):
    cfg = DummyConfigManager()
    svc = PluginService(cfg)
    # inject dummy manager
    monkeypatch.setattr(svc, "plugin_manager", DummyPluginManager())

    assert svc.initialize() is True
    assert svc.initialized is True
    svc.cleanup()
    assert svc.initialized is False


def test_configure_plugin_and_stats(monkeypatch):
    cfg = DummyConfigManager()
    svc = PluginService(cfg)
    mgr = DummyPluginManager()
    monkeypatch.setattr(svc, "plugin_manager", mgr)

    assert svc.configure_plugin("p1", {"k": 1}) is True
    stats = svc.get_plugin_statistics()
    assert stats["total_plugins"] == 4
    # enabled: p1, tts, ocr (p2 disabled)
    assert stats["enabled_plugins"] == 3
    info = svc.get_plugin_info()
    assert any(p["name"] == "p1" for p in info)


def test_enable_disable(monkeypatch):
    cfg = DummyConfigManager()
    svc = PluginService(cfg)
    mgr = DummyPluginManager()
    monkeypatch.setattr(svc, "plugin_manager", mgr)

    assert svc.disable_plugin("p1") is True
    assert mgr.get_plugin("p1").enabled is False
    assert svc.enable_plugin("p1") is True
    assert mgr.get_plugin("p1").enabled is True


def test_test_plugin_across_types(monkeypatch):
    cfg = DummyConfigManager()
    svc = PluginService(cfg)
    mgr = DummyPluginManager()
    monkeypatch.setattr(svc, "plugin_manager", mgr)

    assert svc.test_plugin("p1") is True  # translation kind
    assert svc.test_plugin("tts") is True  # tts speak path
    assert svc.test_plugin("ocr") is True  # ocr path returns True
    assert svc.test_plugin("unknown") is False


def test_test_plugin_unavailable(monkeypatch):
    cfg = DummyConfigManager()
    svc = PluginService(cfg)
    mgr = DummyPluginManager()
    mgr.registered_plugins["p1"]._available = False
    monkeypatch.setattr(svc, "plugin_manager", mgr)
    assert svc.test_plugin("p1") is False



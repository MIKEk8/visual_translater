from src.services.plugin_service import PluginService
from src.plugins.base_plugin import TranslationPlugin, PluginMetadata, PluginType


class DummyConfigManager:
    def add_observer(self, obs):
        pass


class FailingPlugin:
    def __init__(self, initialized=False):
        self.enabled = True
        self._available = True
        self.initialized = initialized

    def is_available(self):
        return True

    def validate_config(self, cfg):
        return False, ["bad"]

    def initialize(self, cfg):
        return False

    def cleanup(self):
        pass


class ExplodingPlugin:
    def __init__(self):
        self.enabled = True
        self.initialized = True

    def is_available(self):
        return True

    def validate_config(self, cfg):
        raise RuntimeError("boom")


class DummyPluginManager:
    def __init__(self):
        self.registered_plugins = {
            "fail": FailingPlugin(initialized=True),
            "explode": ExplodingPlugin(),
        }
        self.plugin_configs = {}

    def load_plugin_config(self, path):
        return True

    def save_plugin_config(self, path):
        return True

    def load_all_plugins(self):
        return len(self.registered_plugins)

    def get_plugin(self, name):
        return self.registered_plugins.get(name)

    def unregister_plugin(self, name):
        self.registered_plugins.pop(name, None)


def test_configure_plugin_not_found(monkeypatch):
    svc = PluginService(DummyConfigManager())
    monkeypatch.setattr(svc, "plugin_manager", DummyPluginManager())
    assert svc.configure_plugin("unknown", {"x": 1}) is False


def test_configure_plugin_invalid_config(monkeypatch):
    svc = PluginService(DummyConfigManager())
    mgr = DummyPluginManager()
    monkeypatch.setattr(svc, "plugin_manager", mgr)
    # FailingPlugin.validate_config returns (False, [errors])
    assert svc.configure_plugin("fail", {"k": 1}) is False


def test_configure_plugin_reinit_fails(monkeypatch):
    class ReinitFailPlugin(FailingPlugin):
        def validate_config(self, cfg):
            return True, []

        def initialize(self, cfg):
            return False

    mgr = DummyPluginManager()
    mgr.registered_plugins["reinit"] = ReinitFailPlugin(initialized=True)

    svc = PluginService(DummyConfigManager())
    monkeypatch.setattr(svc, "plugin_manager", mgr)
    assert svc.configure_plugin("reinit", {"k": 1}) is False


def test_configure_plugin_exception(monkeypatch):
    svc = PluginService(DummyConfigManager())
    mgr = DummyPluginManager()
    monkeypatch.setattr(svc, "plugin_manager", mgr)
    assert svc.configure_plugin("explode", {"k": 1}) is False


def test_test_plugin_exception_path(monkeypatch):
    class BadTranslate(TranslationPlugin):
        @property
        def metadata(self):
            return PluginMetadata(
                name="bad",
                version="1.0",
                description="bad",
                author="t",
                plugin_type=PluginType.TRANSLATION,
            )

        def initialize(self, config):
            return True

        def cleanup(self):
            pass

        def get_supported_languages(self):
            return ["en", "ru"]

        def translate(self, *args, **kwargs):
            raise RuntimeError("fail")

    class Mgr(DummyPluginManager):
        def __init__(self):
            super().__init__()
            self.registered_plugins["bad"] = BadTranslate()

        def get_plugin(self, name):
            return self.registered_plugins.get(name)

    svc = PluginService(DummyConfigManager())
    monkeypatch.setattr(svc, "plugin_manager", Mgr())
    assert svc.test_plugin("bad") is False



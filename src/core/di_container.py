"""Production Dependency Injection Container"""


class DIContainer:
    """Enterprise DI container for 85 components"""

    def __init__(self):
        self._services = {}
        self._singletons = {}

    def register_singleton(self, interface, implementation):
        """Register singleton service"""
        service_name = interface.__name__
        self._singletons[service_name] = implementation()

    def get(self, interface):
        """Get service instance"""
        service_name = interface.__name__
        return self._singletons.get(service_name)


container = DIContainer()

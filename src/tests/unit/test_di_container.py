import unittest
from typing import Any, Dict
from unittest.mock import Mock, patch

from src.services.container import DIContainer, setup_default_services


class __TestService:
    """Test service class"""

    def __init__(self):
        self.initialized = True


class ___TestServiceWithDependency:
    """Test service with dependency"""

    def __init__(self, dependency: '__TestService'):
        self.dependency = dependency


class TestAbstractService:
    """Abstract service interface"""

    pass


class __TestConcreteService(TestAbstractService):
    """Concrete implementation"""

    def __init__(self):
        self.value = "concrete"


class TestDIContainer(unittest.TestCase):
    """Test Dependency Injection Container"""

    def setUp(self):
        """Setup test environment"""
        self.container = DIContainer()

    def test_register_and_get_singleton(self):
        """Test singleton registration and retrieval"""
        self.container.register_singleton(_TestService, _TestService)

        # Get instance twice
        instance1 = self.container.get(_TestService)
        instance2 = self.container.get(_TestService)

        # Should be same instance
        self.assertIs(instance1, instance2)
        self.assertTrue(instance1.initialized)

    def test_register_and_get_transient(self):
        """Test transient registration and retrieval"""
        self.container.register_transient(_TestService, _TestService)

        # Get instance twice
        instance1 = self.container.get(_TestService)
        instance2 = self.container.get(_TestService)

        # Should be different instances
        self.assertIsNot(instance1, instance2)
        self.assertTrue(instance1.initialized)
        self.assertTrue(instance2.initialized)

    def test_register_factory(self):
        """Test factory registration"""
        counter = {"value": 0}

        def factory():
            counter["value"] += 1
            service = __TestService()
            service.counter = counter["value"]
            return service

        self.container.register_factory(_TestService, factory)

        # Get instances
        instance1 = self.container.get(_TestService)
        instance2 = self.container.get(_TestService)

        # Factory should be called each time
        self.assertEqual(instance1.counter, 1)
        self.assertEqual(instance2.counter, 2)

    def test_register_instance(self):
        """Test instance registration"""
        instance = __TestService()
        instance.custom_value = "test"

        self.container.register_instance(_TestService, instance)

        # Should get same instance
        retrieved = self.container.get(_TestService)
        self.assertIs(retrieved, instance)
        self.assertEqual(retrieved.custom_value, "test")

    def test_unregistered_service_error(self):
        """Test error for unregistered service"""
        with self.assertRaises(ValueError) as context:
            self.container.get(_TestService)

        self.assertIn("Service not registered", str(context.exception))

    def test_clear_container(self):
        """Test clearing container"""
        self.container.register_singleton(_TestService, _TestService)
        self.container.get(_TestService)

        # Clear container
        self.container.clear()

        # Should raise error after clear
        with self.assertRaises(ValueError):
            self.container.get(_TestService)

    def test_get_registered_services(self):
        """Test getting service information"""
        self.container.register_singleton(_TestService, _TestService)
        self.container.register_factory(
            __TestServiceWithDependency, lambda: ___TestServiceWithDependency(__TestService())
        )

        services = self.container.get_registered_services()

        # Check service info
        # Check that a service key contains _TestService
        test_service_keys = [k for k in services.keys() if "_TestService" in k]
        self.assertGreater(len(test_service_keys), 0)
        service_info = services[test_service_keys[0]]
        self.assertTrue(service_info["singleton"])
        self.assertEqual(service_info["implementation"], "_TestService")

    def test_key_generation(self):
        """Test internal key generation"""
        key = self.container._get_key(_TestService)
        # Key should end with the class name
        self.assertTrue(key.endswith("_TestService"))
        # Key should include module information
        self.assertIn("test_di_container", key)

    def test_register_abstract_interface(self):
        """Test registering with abstract interface"""
        self.container.register_singleton(TestAbstractService, _TestConcreteService)

        # Should get concrete implementation
        instance = self.container.get(TestAbstractService)
        self.assertIsInstance(instance, _TestConcreteService)
        self.assertEqual(instance.value, "concrete")

    def test_factory_with_dependencies(self):
        """Test factory that creates dependencies"""

        def complex_factory():
            dependency = __TestService()
            dependency.custom_attribute = "injected"
            return ___TestServiceWithDependency(dependency)

        self.container.register_factory(__TestServiceWithDependency, complex_factory)

        instance = self.container.get(__TestServiceWithDependency)
        self.assertIsInstance(instance.dependency, _TestService)
        self.assertEqual(instance.dependency.custom_attribute, "injected")

    def test_multiple_registrations_override(self):
        """Test that later registrations override earlier ones"""
        # First registration
        self.container.register_singleton(_TestService, _TestService)
        instance1 = self.container.get(_TestService)

        # Override with transient - need to clear singleton cache first
        self.container.register_transient(_TestService, _TestService)
        # Clear any cached singleton instance
        key = self.container._get_key(_TestService)
        if key in self.container._singletons:
            del self.container._singletons[key]

        instance2 = self.container.get(_TestService)
        instance3 = self.container.get(_TestService)

        # Should create new instances now
        self.assertIsNot(instance2, instance3)

    def test_circular_dependency_detection(self):
        """Test handling of circular dependencies"""

        # This would cause infinite recursion in real scenario
        # For now, just test that creation fails gracefully
        class ServiceA:
            def __init__(self):
                # Would need ServiceB which needs ServiceA
                raise RuntimeError("Circular dependency")

        self.container.register_singleton(ServiceA, ServiceA)

        with self.assertRaises(RuntimeError):
            self.container.get(ServiceA)

    def test_get_registered_services_comprehensive(self):
        """Test comprehensive service information"""
        # Register various types
        self.container.register_singleton(_TestService, _TestService)
        self.container.register_transient(TestAbstractService, _TestConcreteService)
        self.container.register_factory(
            __TestServiceWithDependency, lambda: ___TestServiceWithDependency(__TestService())
        )
        instance = __TestService()
        self.container.register_instance(_TestService, instance)

        services = self.container.get_registered_services()

        # Should have entries for all registered services
        self.assertIn(self.container._get_key(_TestService), services)
        self.assertIn(self.container._get_key(TestAbstractService), services)
        self.assertIn(self.container._get_key(__TestServiceWithDependency), services)

    def test_create_instance_error_handling(self):
        """Test error handling in _create_instance"""

        class FailingService:
            def __init__(self):
                raise ValueError("Initialization failed")

        self.container.register_singleton(FailingService, FailingService)

        with self.assertRaises(ValueError) as context:
            self.container.get(FailingService)

        self.assertIn("Initialization failed", str(context.exception))

    @patch("src.services.container.logger")
    def test_logging_operations(self, mock_logger):
        """Test that operations are properly logged"""
        # Test singleton registration
        self.container.register_singleton(_TestService, _TestService)
        mock_logger.debug.assert_called()

        # Test instance creation
        self.container.get(_TestService)
        # Should have multiple debug calls
        self.assertGreater(mock_logger.debug.call_count, 1)

    def test_setup_default_services(self):
        """Test setup_default_services function"""
        test_container = DIContainer()

        # Mock PIL and other dependencies that may not be available
        with patch.dict(
            "sys.modules",
            {
                "PIL": Mock(),
                "PIL.Image": Mock(),
                "PIL.ImageEnhance": Mock(),
                "PIL.ImageFilter": Mock(),
                "pytesseract": Mock(),
                "pyttsx3": Mock(),
                "googletrans": Mock(),
            },
        ):
            with patch("src.services.container.logger"):
                try:
                    setup_default_services(test_container)

                    # Should have registered services
                    services = test_container.get_registered_services()
                    self.assertGreater(len(services), 0)
                except ImportError as e:
                    # Skip test if dependencies not available
                    self.skipTest(f"Required dependencies not available: {e}")

        # Check for key services
        config_manager_key = "src.services.config_manager.ConfigManager"
        self.assertIn(config_manager_key, services)

    def test_singleton_thread_safety(self):
        """Test singleton creation is thread-safe"""
        import threading

        instances = []
        errors = []

        def get_instance():
            try:
                instance = self.container.get(_TestService)
                instances.append(instance)
            except Exception as e:
                errors.append(e)

        self.container.register_singleton(_TestService, _TestService)

        # Create multiple threads trying to get singleton
        threads = [threading.Thread(target=get_instance, daemon=True) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have no errors
        self.assertEqual(len(errors), 0)

        # All instances should be the same
        if instances:
            first_instance = instances[0]
            for instance in instances[1:]:
                self.assertIs(instance, first_instance)

    def test_register_none_implementation(self):
        """Test registering None as implementation"""
        # This should register successfully but fail when trying to create instance
        self.container.register_singleton(_TestService, None)
        with self.assertRaises(TypeError):
            self.container.get(_TestService)

    def test_factory_returning_none(self):
        """Test factory that returns None"""
        self.container.register_factory(_TestService, lambda: None)

        result = self.container.get(_TestService)
        self.assertIsNone(result)

    def test_complex_service_graph(self):
        """Test complex dependency graph"""

        # Create a more complex dependency scenario
        class ServiceA:
            pass

        class ServiceB:
            def __init__(self):
                self.a = self.container.get(ServiceA) if hasattr(self, "container") else ServiceA()

        class ServiceC:
            def __init__(self):
                self.a = ServiceA()
                self.b = ServiceB()

        self.container.register_singleton(ServiceA, ServiceA)
        self.container.register_transient(ServiceB, ServiceB)
        self.container.register_factory(ServiceC, ServiceC)

        # Should be able to resolve all
        a = self.container.get(ServiceA)
        b = self.container.get(ServiceB)
        c = self.container.get(ServiceC)

        self.assertIsInstance(a, ServiceA)
        self.assertIsInstance(b, ServiceB)
        self.assertIsInstance(c, ServiceC)


if __name__ == "__main__":
    unittest.main()

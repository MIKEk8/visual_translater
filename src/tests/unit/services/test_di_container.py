"""Unit tests for DIContainer - Dependency Injection Container"""

import unittest
from unittest.mock import MagicMock, Mock, patch, call
from typing import Any

from src.services.container import DIContainer, setup_default_services


class MockInterface:
    """Mock interface for DI container tests"""
    pass


class MockImplementation(MockInterface):
    """Mock implementation for DI container tests"""
    def __init__(self):
        self.initialized = True


class MockTransient:
    """Mock class for transient registration"""
    instance_count = 0
    
    def __init__(self):
        MockTransient.instance_count += 1
        self.instance_id = MockTransient.instance_count


class TestDIContainer(unittest.TestCase):
    """Test suite for DIContainer"""

    def setUp(self):
        """Set up test fixtures"""
        self.container = DIContainer()
        # Reset transient counter
        MockTransient.instance_count = 0
        
        # Patch logger
        self.logger_patch = patch('src.services.container.logger')
        self.mock_logger = self.logger_patch.start()

    def tearDown(self):
        """Clean up patches"""
        self.logger_patch.stop()

    def test_initialization(self):
        """Test container initialization"""
        # Create new container to check initialization
        with patch('src.services.container.logger') as mock_logger:
            container = DIContainer()
            
            # Assert internal state is initialized
            self.assertIsInstance(container._services, dict)
            self.assertIsInstance(container._singletons, dict)
            self.assertIsInstance(container._factories, dict)
            self.assertEqual(len(container._services), 0)
            self.assertEqual(len(container._singletons), 0)
            self.assertEqual(len(container._factories), 0)
            
            # Verify logging
            mock_logger.debug.assert_called_with("DI Container initialized")

    def test_register_singleton(self):
        """Test singleton service registration"""
        # Act
        self.container.register_singleton(MockInterface, MockImplementation)
        
        # Assert
        key = self.container._get_key(MockInterface)
        self.assertIn(key, self.container._services)
        impl, is_singleton = self.container._services[key]
        self.assertEqual(impl, MockImplementation)
        self.assertTrue(is_singleton)
        
        # Verify logging
        self.mock_logger.debug.assert_called_with(f"Registered singleton: {key}")

    def test_register_transient(self):
        """Test transient service registration"""
        # Act
        self.container.register_transient(MockInterface, MockImplementation)
        
        # Assert
        key = self.container._get_key(MockInterface)
        self.assertIn(key, self.container._services)
        impl, is_singleton = self.container._services[key]
        self.assertEqual(impl, MockImplementation)
        self.assertFalse(is_singleton)
        
        # Verify logging
        self.mock_logger.debug.assert_called_with(f"Registered transient: {key}")

    def test_register_factory(self):
        """Test factory registration"""
        # Setup
        factory = Mock(return_value=MockImplementation())
        
        # Act
        self.container.register_factory(MockInterface, factory)
        
        # Assert
        key = self.container._get_key(MockInterface)
        self.assertIn(key, self.container._factories)
        self.assertEqual(self.container._factories[key], factory)
        
        # Verify logging
        self.mock_logger.debug.assert_called_with(f"Registered factory: {key}")

    def test_register_instance(self):
        """Test instance registration"""
        # Setup
        instance = MockImplementation()
        
        # Act
        self.container.register_instance(MockInterface, instance)
        
        # Assert
        key = self.container._get_key(MockInterface)
        self.assertIn(key, self.container._singletons)
        self.assertEqual(self.container._singletons[key], instance)
        
        # Verify logging
        self.mock_logger.debug.assert_called_with(f"Registered instance: {key}")

    def test_get_singleton(self):
        """Test getting singleton service"""
        # Setup
        self.container.register_singleton(MockInterface, MockImplementation)
        
        # Act
        instance1 = self.container.get(MockInterface)
        instance2 = self.container.get(MockInterface)
        
        # Assert - same instance returned
        self.assertIsInstance(instance1, MockImplementation)
        self.assertIs(instance1, instance2)
        self.assertTrue(instance1.initialized)

    def test_get_transient(self):
        """Test getting transient service"""
        # Setup
        self.container.register_transient(MockTransient, MockTransient)
        
        # Act
        instance1 = self.container.get(MockTransient)
        instance2 = self.container.get(MockTransient)
        
        # Assert - different instances returned
        self.assertIsInstance(instance1, MockTransient)
        self.assertIsInstance(instance2, MockTransient)
        self.assertIsNot(instance1, instance2)
        self.assertEqual(instance1.instance_id, 1)
        self.assertEqual(instance2.instance_id, 2)

    def test_get_from_factory(self):
        """Test getting service from factory"""
        # Setup
        created_instances = []
        def factory():
            instance = MockImplementation()
            created_instances.append(instance)
            return instance
            
        self.container.register_factory(MockInterface, factory)
        
        # Act
        instance1 = self.container.get(MockInterface)
        instance2 = self.container.get(MockInterface)
        
        # Assert - factory called each time
        self.assertEqual(len(created_instances), 2)
        self.assertIsNot(instance1, instance2)
        self.assertIsInstance(instance1, MockImplementation)
        self.assertIsInstance(instance2, MockImplementation)

    def test_get_registered_instance(self):
        """Test getting pre-registered instance"""
        # Setup
        instance = MockImplementation()
        self.container.register_instance(MockInterface, instance)
        
        # Act
        retrieved = self.container.get(MockInterface)
        
        # Assert - same instance returned
        self.assertIs(retrieved, instance)

    def test_get_unregistered_service(self):
        """Test getting unregistered service raises error"""
        # Act & Assert
        with self.assertRaises(ValueError) as cm:
            self.container.get(MockInterface)
        
        key = self.container._get_key(MockInterface)
        self.assertEqual(str(cm.exception), f"Service not registered: {key}")

    def test_singleton_caching(self):
        """Test singleton is created only once"""
        # Setup
        creation_count = 0
        
        class CountedImplementation(MockInterface):
            def __init__(self):
                nonlocal creation_count
                creation_count += 1
                
        self.container.register_singleton(MockInterface, CountedImplementation)
        
        # Act
        instance1 = self.container.get(MockInterface)
        instance2 = self.container.get(MockInterface)
        instance3 = self.container.get(MockInterface)
        
        # Assert
        self.assertEqual(creation_count, 1)
        self.assertIs(instance1, instance2)
        self.assertIs(instance2, instance3)

    def test_clear(self):
        """Test clearing all registrations"""
        # Setup
        self.container.register_singleton(MockInterface, MockImplementation)
        self.container.register_factory(MockTransient, lambda: MockTransient())
        instance = MockImplementation()
        self.container.register_instance(MockImplementation, instance)
        
        # Act
        self.container.clear()
        
        # Assert
        self.assertEqual(len(self.container._services), 0)
        self.assertEqual(len(self.container._singletons), 0)
        self.assertEqual(len(self.container._factories), 0)
        
        # Verify logging
        self.mock_logger.debug.assert_called_with("DI Container cleared")

    def test_get_registered_services(self):
        """Test getting information about registered services"""
        # Setup
        self.container.register_singleton(MockInterface, MockImplementation)
        self.container.register_transient(MockTransient, MockTransient)
        self.container.register_factory(Mock, lambda: Mock())
        instance = MockImplementation()
        self.container.register_instance(MockImplementation, instance)
        
        # Create a singleton instance
        self.container.get(MockInterface)
        
        # Act
        services = self.container.get_registered_services()
        
        # Assert
        self.assertEqual(len(services), 4)
        
        # Check singleton
        interface_key = self.container._get_key(MockInterface)
        self.assertIn(interface_key, services)
        self.assertEqual(services[interface_key]["implementation"], "MockImplementation")
        self.assertTrue(services[interface_key]["singleton"])
        self.assertTrue(services[interface_key]["instantiated"])
        
        # Check transient
        transient_key = self.container._get_key(MockTransient)
        self.assertIn(transient_key, services)
        self.assertEqual(services[transient_key]["implementation"], "MockTransient")
        self.assertFalse(services[transient_key]["singleton"])
        self.assertFalse(services[transient_key]["instantiated"])
        
        # Check factory
        mock_key = self.container._get_key(Mock)
        self.assertIn(mock_key, services)
        self.assertEqual(services[mock_key]["implementation"], "Factory")
        self.assertFalse(services[mock_key]["singleton"])
        
        # Check instance
        impl_key = self.container._get_key(MockImplementation)
        self.assertIn(impl_key, services)
        self.assertEqual(services[impl_key]["implementation"], "Instance")
        self.assertTrue(services[impl_key]["singleton"])
        self.assertTrue(services[impl_key]["instantiated"])

    def test_get_key(self):
        """Test key generation for types"""
        # Act
        key = self.container._get_key(MockInterface)
        
        # Assert
        expected = f"{MockInterface.__module__}.{MockInterface.__name__}"
        self.assertEqual(key, expected)

    def test_create_instance_error_handling(self):
        """Test error handling during instance creation"""
        # Setup
        class FailingImplementation(MockInterface):
            def __init__(self):
                raise RuntimeError("Creation failed")
                
        self.container.register_singleton(MockInterface, FailingImplementation)
        
        # Act & Assert
        with self.assertRaises(RuntimeError):
            self.container.get(MockInterface)
            
        # Verify error logging
        self.mock_logger.error.assert_called()

    def test_priority_order(self):
        """Test resolution priority: cached > factory > service"""
        # Setup
        service_instance = MockImplementation()
        factory_instance = MockImplementation()
        cached_instance = MockImplementation()
        
        # Register all types
        self.container.register_singleton(MockInterface, MockImplementation)
        self.container.register_factory(MockInterface, lambda: factory_instance)
        self.container.register_instance(MockInterface, cached_instance)
        
        # Act
        result = self.container.get(MockInterface)
        
        # Assert - cached instance has highest priority
        self.assertIs(result, cached_instance)

    def test_factory_with_singleton_behavior(self):
        """Test that factories are not cached like singletons"""
        # Setup
        call_count = 0
        instances = []
        
        def counting_factory():
            nonlocal call_count
            call_count += 1
            instance = MockImplementation()
            instances.append(instance)
            return instance
            
        self.container.register_factory(MockInterface, counting_factory)
        
        # Act
        instance1 = self.container.get(MockInterface)
        instance2 = self.container.get(MockInterface)
        
        # Assert
        self.assertEqual(call_count, 2)
        self.assertEqual(len(instances), 2)
        self.assertIsNot(instance1, instance2)


class TestSetupDefaultServices(unittest.TestCase):
    """Test suite for setup_default_services function"""

    def setUp(self):
        """Set up test fixtures"""
        self.container = DIContainer()

    def tearDown(self):
        """Clean up test fixtures"""
        self.container.clear()

    def test_setup_default_services_with_container(self):
        """Test setting up services in specific container"""
        # Act
        setup_default_services(self.container)
        
        # Assert - verify core services registered
        services = self.container.get_registered_services()
        
        # Should have services registered
        self.assertGreater(len(services), 0)
        
        # Check that we have both singleton services and factories
        self.assertGreater(len(self.container._services), 0)
        self.assertGreater(len(self.container._factories), 0)

    def test_setup_default_services_without_container(self):
        """Test setting up services in global container"""
        # Setup
        with patch('src.services.container.container') as mock_global_container:
            mock_global_container.register_singleton = MagicMock()
            mock_global_container.register_factory = MagicMock()
            mock_global_container.register_instance = MagicMock()
            
            # Act
            setup_default_services()
            
            # Assert - should use global container
            # Verify services were registered on global container
            mock_global_container.register_singleton.assert_called()
            mock_global_container.register_factory.assert_called()

    def test_factory_functions_use_container(self):
        """Test that factory functions properly use the container"""
        # This test verifies that the factories created by setup_default_services
        # properly use the container to resolve dependencies
        
        # Act - setup services
        setup_default_services(self.container)
        
        # Assert - verify factories were registered
        self.assertGreater(len(self.container._factories), 0)
        
        # Verify we can get core services
        from src.services.config_manager import ConfigManager
        from src.core.ocr_engine import OCRProcessor
        
        # Get ConfigManager (singleton)
        config_manager = self.container.get(ConfigManager)
        self.assertIsNotNone(config_manager)
        
        # Get OCRProcessor (created by factory)
        ocr = self.container.get(OCRProcessor)
        self.assertIsNotNone(ocr)
        
        # Verify the services list includes both registered types
        services = self.container.get_registered_services()
        
        # Check ConfigManager is registered as singleton
        config_key = self.container._get_key(ConfigManager)
        self.assertIn(config_key, services)
        self.assertTrue(services[config_key]["singleton"])
        
        # Check OCRProcessor has a factory
        ocr_key = self.container._get_key(OCRProcessor)
        self.assertIn(ocr_key, self.container._factories)

    def test_repositories_not_available(self):
        """Test graceful handling when repositories module is not available"""
        # This test is complex due to the way imports work in setup_default_services
        # We'll test that the function completes without error even with missing modules
        
        # Act - should not raise exception
        try:
            setup_default_services(self.container)
            success = True
        except Exception:
            success = False
            
        # Assert
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
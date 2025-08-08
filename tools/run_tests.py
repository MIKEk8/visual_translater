#!/usr/bin/env python3
"""
Test runner script for Screen Translator v2.0
Runs all tests and generates coverage report
"""

import sys
import os
import subprocess
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def run_tests():
    """Run all tests with coverage"""
    
    print("=" * 60)
    print("  Screen Translator v2.0 - Test Runner")
    print("=" * 60)
    
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        print("[ERROR] pytest not installed. Please run: pip install pytest pytest-cov")
        return 1
    
    # Test command with coverage
    test_args = [
        "-v",  # Verbose output
        "--cov=src",  # Coverage for src directory
        "--cov-report=term-missing",  # Show missing lines in terminal
        "--cov-report=html:htmlcov",  # Generate HTML report
        "--cov-report=xml:coverage.xml",  # Generate XML report
        "--tb=short",  # Short traceback format
        "src/tests",  # Test directory
    ]
    
    # Add color if terminal supports it
    if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        test_args.insert(0, "--color=yes")
    
    print(f"\n[INFO] Running tests with arguments: {' '.join(test_args)}\n")
    
    # Run pytest
    exit_code = pytest.main(test_args)
    
    if exit_code == 0:
        print("\n[SUCCESS] All tests passed!")
        
        # Show coverage summary
        print("\n[INFO] Coverage report generated:")
        print("  - Terminal report: See above")
        print("  - HTML report: htmlcov/index.html")
        print("  - XML report: coverage.xml")
        
        # Try to get coverage percentage
        try:
            with open("coverage.xml", "r") as f:
                import xml.etree.ElementTree as ET
                tree = ET.parse(f)
                root = tree.getroot()
                coverage_percent = float(root.get('line-rate', 0)) * 100
                print(f"\n[INFO] Overall coverage: {coverage_percent:.1f}%")
        except:
            pass
            
    else:
        print(f"\n[ERROR] Tests failed with exit code: {exit_code}")
    
    return exit_code


def run_specific_test(test_path):
    """Run a specific test file or test case"""
    
    print(f"\n[INFO] Running specific test: {test_path}")
    
    test_args = [
        "-v",
        "--tb=short",
        test_path
    ]
    
    return pytest.main(test_args)


def run_test_suite(suite_name):
    """Run a specific test suite"""
    
    suites = {
        "unit": "src/tests/unit",
        "integration": "src/tests/integration",
        "core": "src/tests/unit/test_*engine*.py src/tests/unit/test_application.py",
        "services": "src/tests/unit/test_*service*.py src/tests/unit/test_*cache*.py",
        "models": "src/tests/unit/test_*model*.py src/tests/unit/test_config*.py",
        "utils": "src/tests/unit/test_logger.py src/tests/unit/test_exceptions.py src/tests/unit/test_*monitor*.py",
    }
    
    if suite_name not in suites:
        print(f"[ERROR] Unknown test suite: {suite_name}")
        print(f"Available suites: {', '.join(suites.keys())}")
        return 1
    
    print(f"\n[INFO] Running {suite_name} test suite")
    
    test_args = ["-v", "--tb=short"]
    test_args.extend(suites[suite_name].split())
    
    return pytest.main(test_args)


def check_test_requirements():
    """Check if all test requirements are installed"""
    
    required_packages = [
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "pytest-asyncio",
    ]
    
    missing = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"[WARNING] Missing test packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    
    return True


def main():
    """Main entry point"""
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "help" or command == "--help":
            print("Usage: python run_tests.py [command] [args]")
            print("\nCommands:")
            print("  all          - Run all tests with coverage (default)")
            print("  unit         - Run unit tests only")
            print("  integration  - Run integration tests only")
            print("  core         - Run core component tests")
            print("  services     - Run service tests")
            print("  models       - Run model tests")
            print("  utils        - Run utility tests")
            print("  file <path>  - Run specific test file")
            print("  check        - Check test requirements")
            print("\nExamples:")
            print("  python run_tests.py")
            print("  python run_tests.py unit")
            print("  python run_tests.py file src/tests/unit/test_application.py")
            return 0
            
        elif command == "check":
            if check_test_requirements():
                print("[OK] All test requirements installed")
                return 0
            else:
                return 1
                
        elif command == "file" and len(sys.argv) > 2:
            return run_specific_test(sys.argv[2])
            
        elif command in ["all", "unit", "integration", "core", "services", "models", "utils"]:
            if command == "all":
                return run_tests()
            else:
                return run_test_suite(command)
        else:
            print(f"[ERROR] Unknown command: {command}")
            print("Run 'python run_tests.py help' for usage")
            return 1
    
    # Default: run all tests
    if not check_test_requirements():
        print("\n[ERROR] Missing test requirements. Cannot run tests.")
        return 1
        
    return run_tests()


if __name__ == "__main__":
    sys.exit(main())
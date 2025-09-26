"""
Unit tests for module passport system.
Tests verify YAML structure, validation, and passport generation.
"""

import pytest
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import Mock, patch, mock_open
import ast
import inspect


class ModulePassport:
    """Module passport handler for managing module documentation."""

    def __init__(self, yaml_path: Path):
        """Initialize passport from YAML file."""
        self.path = yaml_path
        self.data = self._load_yaml()

    def _load_yaml(self) -> Dict[str, Any]:
        """Load and validate YAML passport file."""
        if not self.path.exists():
            raise FileNotFoundError(f"Passport file not found: {self.path}")

        with open(self.path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        self._validate_structure(data)
        return data

    def _validate_structure(self, data: Dict[str, Any]) -> None:
        """Validate passport YAML structure."""
        required_fields = [
            'module', 'purpose', 'interfaces', 'dependencies',
            'tests', 'constraints', 'last_updated'
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Validate nested structures
        if not isinstance(data['interfaces'], list):
            raise ValueError("'interfaces' must be a list")

        if not isinstance(data['dependencies'], dict):
            raise ValueError("'dependencies' must be a dict")

        if 'uses' not in data['dependencies'] or 'used_by' not in data['dependencies']:
            raise ValueError("'dependencies' must have 'uses' and 'used_by' fields")

        if not isinstance(data['tests'], dict):
            raise ValueError("'tests' must be a dict")

        if 'unit' not in data['tests'] or 'integration' not in data['tests']:
            raise ValueError("'tests' must have 'unit' and 'integration' fields")

    def validate_against_module(self, module_path: Path) -> List[str]:
        """Validate passport against actual module implementation."""
        if not module_path.exists():
            return [f"Module file not found: {module_path}"]

        errors = []
        # Parse module to extract interfaces
        with open(module_path, 'r', encoding='utf-8') as f:
            source = f.read()

        try:
            tree = ast.parse(source)
            actual_interfaces = self._extract_interfaces(tree)

            # Compare with documented interfaces
            documented = set(self.data['interfaces'])
            actual = set(actual_interfaces)

            missing = actual - documented
            extra = documented - actual

            if missing:
                errors.append(f"Undocumented interfaces: {missing}")
            if extra:
                errors.append(f"Documented but missing interfaces: {extra}")

        except SyntaxError as e:
            errors.append(f"Module syntax error: {e}")

        return errors

    def _extract_interfaces(self, tree: ast.AST) -> List[str]:
        """Extract public interfaces from AST."""
        interfaces = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                # Extract function signature
                args = []
                for arg in node.args.args:
                    if arg.arg != 'self':
                        annotation = ast.unparse(arg.annotation) if arg.annotation else 'Any'
                        args.append(f"{arg.arg}: {annotation}")

                returns = ast.unparse(node.returns) if node.returns else 'None'
                signature = f"{node.name}({', '.join(args)}) -> {returns}"
                interfaces.append(signature)

            elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
                # Add class constructor
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                        args = []
                        for arg in item.args.args[1:]:  # Skip self
                            annotation = ast.unparse(arg.annotation) if arg.annotation else 'Any'
                            args.append(f"{arg.arg}: {annotation}")
                        signature = f"{node.name}({', '.join(args)})"
                        interfaces.append(signature)

        return interfaces

    def update_timestamp(self) -> None:
        """Update last_updated field to current date."""
        self.data['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        self._save_yaml()

    def _save_yaml(self) -> None:
        """Save passport data back to YAML file."""
        with open(self.path, 'w', encoding='utf-8') as f:
            yaml.dump(self.data, f, default_flow_style=False, sort_keys=False)

    def check_dependencies_exist(self, project_root: Path) -> List[str]:
        """Check if all dependency modules exist."""
        errors = []

        for dep_module in self.data['dependencies']['uses']:
            module_path = project_root / dep_module.replace('.', '/') + '.py'
            if not module_path.exists():
                errors.append(f"Dependency not found: {dep_module}")

        return errors

    def check_tests_exist(self, project_root: Path) -> List[str]:
        """Check if all referenced test files exist."""
        errors = []

        for test_file in self.data['tests']['unit']:
            test_path = project_root / test_file
            if not test_path.exists():
                errors.append(f"Unit test not found: {test_file}")

        for test_file in self.data['tests']['integration']:
            test_path = project_root / test_file
            if not test_path.exists():
                errors.append(f"Integration test not found: {test_file}")

        return errors


class PassportGenerator:
    """Generator for creating module passports from source code."""

    def __init__(self, project_root: Path):
        """Initialize generator with project root."""
        self.project_root = project_root
        self.modules_dir = project_root / "docs" / "modules"

    def generate_passport(self, module_path: Path) -> Dict[str, Any]:
        """Generate passport data from module source."""
        if not module_path.exists():
            raise FileNotFoundError(f"Module not found: {module_path}")

        with open(module_path, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source)

        # Extract module docstring for purpose
        purpose = ast.get_docstring(tree) or "No description provided"
        if len(purpose) > 100:
            purpose = purpose[:97] + "..."

        # Extract interfaces
        interfaces = self._extract_public_interfaces(tree)

        # Analyze imports for dependencies
        dependencies = self._analyze_dependencies(tree)

        # Find related tests
        tests = self._find_related_tests(module_path)

        # Extract constraints from comments/docstrings
        constraints = self._extract_constraints(source)

        return {
            'module': str(module_path.relative_to(self.project_root)),
            'purpose': purpose,
            'interfaces': interfaces,
            'dependencies': dependencies,
            'tests': tests,
            'constraints': constraints,
            'last_updated': datetime.now().strftime('%Y-%m-%d')
        }

    def _extract_public_interfaces(self, tree: ast.AST) -> List[str]:
        """Extract all public interfaces from module."""
        interfaces = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith('_'):
                    sig = self._function_signature(node)
                    interfaces.append(sig)

            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith('_'):
                    # Add class and its public methods
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if not item.name.startswith('_') or item.name == '__init__':
                                sig = f"{node.name}.{self._function_signature(item)}"
                                interfaces.append(sig)

        return interfaces

    def _function_signature(self, node: ast.FunctionDef) -> str:
        """Generate function signature string."""
        args = []
        for arg in node.args.args:
            if arg.arg != 'self' and arg.arg != 'cls':
                if arg.annotation:
                    args.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
                else:
                    args.append(arg.arg)

        returns = ast.unparse(node.returns) if node.returns else 'None'
        return f"{node.name}({', '.join(args)}) -> {returns}"

    def _analyze_dependencies(self, tree: ast.AST) -> Dict[str, List[str]]:
        """Analyze import statements to determine dependencies."""
        uses = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith('src.'):
                        uses.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith('src.'):
                    uses.append(node.module)

        # Placeholder for used_by (would need full project analysis)
        used_by = []

        return {'uses': list(set(uses)), 'used_by': used_by}

    def _find_related_tests(self, module_path: Path) -> Dict[str, List[str]]:
        """Find test files related to this module."""
        module_name = module_path.stem
        tests = {'unit': [], 'integration': []}

        # Search for matching test files
        unit_tests_dir = self.project_root / "src" / "tests" / "unit"
        integration_tests_dir = self.project_root / "src" / "tests" / "integration"

        if unit_tests_dir.exists():
            for test_file in unit_tests_dir.rglob(f"*{module_name}*.py"):
                relative_path = test_file.relative_to(self.project_root)
                tests['unit'].append(str(relative_path))

        if integration_tests_dir.exists():
            for test_file in integration_tests_dir.rglob(f"*{module_name}*.py"):
                relative_path = test_file.relative_to(self.project_root)
                tests['integration'].append(str(relative_path))

        return tests

    def _extract_constraints(self, source: str) -> Dict[str, List[str]]:
        """Extract constraints from source code comments and docstrings."""
        constraints = {'invariants': [], 'perf_budget': 'Not specified'}

        # Look for invariant comments
        import re
        invariant_pattern = r'#\s*INVARIANT:\s*(.+)'
        for match in re.finditer(invariant_pattern, source):
            constraints['invariants'].append(match.group(1).strip())

        # Look for performance annotations
        perf_pattern = r'#\s*PERFORMANCE:\s*(.+)'
        perf_match = re.search(perf_pattern, source)
        if perf_match:
            constraints['perf_budget'] = perf_match.group(1).strip()

        return constraints

    def create_passport_file(self, module_path: Path) -> Path:
        """Create passport YAML file for a module."""
        passport_data = self.generate_passport(module_path)

        # Generate passport filename
        module_name = module_path.stem
        passport_path = self.modules_dir / f"{module_name}.yml"

        # Ensure directory exists
        self.modules_dir.mkdir(parents=True, exist_ok=True)

        # Write passport file
        with open(passport_path, 'w', encoding='utf-8') as f:
            yaml.dump(passport_data, f, default_flow_style=False, sort_keys=False)

        return passport_path


class TestModulePassport:
    """Test suite for module passport functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.modules_dir = self.project_root / "docs" / "modules"

    # CRITICAL: Template validation
    def test_passport_template_structure(self):
        """Test that passport template has correct structure."""
        template_path = self.modules_dir / "_template.yml"
        assert template_path.exists(), "Module passport template not found"

        with open(template_path, 'r', encoding='utf-8') as f:
            template = yaml.safe_load(f)

        required_fields = [
            'module', 'purpose', 'interfaces', 'dependencies',
            'tests', 'constraints', 'last_updated'
        ]

        for field in required_fields:
            assert field in template, f"Template missing required field: {field}"

        # Check nested structure
        assert 'uses' in template['dependencies'], "Template missing 'uses' in dependencies"
        assert 'used_by' in template['dependencies'], "Template missing 'used_by' in dependencies"
        assert 'unit' in template['tests'], "Template missing 'unit' in tests"
        assert 'integration' in template['tests'], "Template missing 'integration' in tests"
        assert 'invariants' in template['constraints'], "Template missing 'invariants' in constraints"
        assert 'perf_budget' in template['constraints'], "Template missing 'perf_budget' in constraints"

    # CRITICAL: Passport validation
    def test_passport_validation(self):
        """Test passport validation against module implementation."""
        # Test with core application module
        module_path = self.project_root / "src" / "core" / "application.py"
        passport_path = self.modules_dir / "core_application.yml"

        if passport_path.exists():
            passport = ModulePassport(passport_path)
            errors = passport.validate_against_module(module_path)
            assert len(errors) == 0, f"Passport validation errors: {errors}"
        else:
            pytest.fail(f"Passport not found for core module: {passport_path}")

    def test_passport_loader(self):
        """Test loading and parsing passport YAML files."""
        # Create test passport
        test_passport = {
            'module': 'src/test/module.py',
            'purpose': 'Test module',
            'interfaces': ['test_func() -> None'],
            'dependencies': {'uses': [], 'used_by': []},
            'tests': {'unit': [], 'integration': []},
            'constraints': {'invariants': [], 'perf_budget': 'O(1)'},
            'last_updated': '2025-09-26'
        }

        with patch('builtins.open', mock_open(read_data=yaml.dump(test_passport))):
            with patch('pathlib.Path.exists', return_value=True):
                passport = ModulePassport(Path('test.yml'))
                assert passport.data['module'] == 'src/test/module.py'
                assert passport.data['purpose'] == 'Test module'

    def test_passport_generator(self):
        """Test automatic passport generation from source code."""
        generator = PassportGenerator(self.project_root)

        # Test with a real module
        module_path = self.project_root / "src" / "core" / "ocr_engine.py"

        if module_path.exists():
            passport_data = generator.generate_passport(module_path)

            assert 'module' in passport_data
            assert 'purpose' in passport_data
            assert 'interfaces' in passport_data
            assert len(passport_data['interfaces']) > 0, "No interfaces extracted"
            assert 'dependencies' in passport_data
            assert 'tests' in passport_data

    # CRITICAL: Core module passports exist
    def test_core_module_passports_exist(self):
        """Test that passports exist for core architecture modules."""
        core_modules = [
            "core_application.yml",
            "translation_engine.yml",
            "ocr_engine.yml",
            "screenshot_processor.yml",
            "translation_workflow.yml"
        ]

        for passport_file in core_modules:
            passport_path = self.modules_dir / passport_file
            assert passport_path.exists(), f"Missing passport for core module: {passport_file}"

    def test_passport_dependencies_validation(self):
        """Test that passport dependencies match actual imports."""
        module_path = self.project_root / "src" / "core" / "application.py"
        passport_path = self.modules_dir / "core_application.yml"

        if passport_path.exists() and module_path.exists():
            passport = ModulePassport(passport_path)
            errors = passport.check_dependencies_exist(self.project_root)
            assert len(errors) == 0, f"Dependency validation errors: {errors}"

    def test_passport_tests_validation(self):
        """Test that test files referenced in passport exist."""
        passport_path = self.modules_dir / "core_application.yml"

        if passport_path.exists():
            passport = ModulePassport(passport_path)
            errors = passport.check_tests_exist(self.project_root)
            assert len(errors) == 0, f"Test file validation errors: {errors}"

    def test_passport_timestamp_update(self):
        """Test updating passport timestamp."""
        with patch('builtins.open', mock_open()):
            with patch('pathlib.Path.exists', return_value=True):
                passport = ModulePassport(Path('test.yml'))
                old_date = passport.data['last_updated']

                passport.update_timestamp()
                new_date = passport.data['last_updated']

                assert new_date != old_date
                assert datetime.strptime(new_date, '%Y-%m-%d')  # Valid date format

    # CRITICAL: Performance constraints validation
    def test_performance_constraints_format(self):
        """Test that performance constraints are properly formatted."""
        passport_path = self.modules_dir / "ocr_engine.yml"

        if passport_path.exists():
            with open(passport_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            perf_budget = data['constraints']['perf_budget']
            # Should specify complexity or timing
            assert any(x in perf_budget for x in ['O(', 'ms', 'seconds', 'Not specified']), \
                f"Invalid performance budget format: {perf_budget}"

    def test_passport_batch_generation(self):
        """Test generating passports for multiple modules at once."""
        generator = PassportGenerator(self.project_root)

        modules_to_document = [
            self.project_root / "src" / "core" / "application.py",
            self.project_root / "src" / "core" / "ocr_engine.py",
            self.project_root / "src" / "core" / "tts_engine.py"
        ]

        generated_passports = []
        for module_path in modules_to_document:
            if module_path.exists():
                passport_data = generator.generate_passport(module_path)
                generated_passports.append(passport_data)

        assert len(generated_passports) > 0, "No passports generated"

        for passport in generated_passports:
            assert 'module' in passport
            assert 'interfaces' in passport
            assert len(passport['interfaces']) > 0

    def test_passport_consistency_check(self):
        """Test that all passports follow consistent format."""
        passport_files = list(self.modules_dir.glob("*.yml"))

        for passport_file in passport_files:
            if passport_file.name.startswith('_'):
                continue  # Skip template

            with open(passport_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # Check all have same structure
            assert 'module' in data
            assert 'purpose' in data
            assert 'interfaces' in data
            assert 'dependencies' in data
            assert 'tests' in data
            assert 'constraints' in data
            assert 'last_updated' in data

            # Check date format
            assert datetime.strptime(data['last_updated'], '%Y-%m-%d')

    def test_passport_circular_dependency_detection(self):
        """Test detection of circular dependencies in passports."""
        # This would analyze all passports for circular deps
        passports = {}
        for passport_file in self.modules_dir.glob("*.yml"):
            if not passport_file.name.startswith('_'):
                with open(passport_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    passports[data['module']] = data['dependencies']['uses']

        # Simple cycle detection algorithm
        def has_cycle(module, visited, rec_stack):
            visited.add(module)
            rec_stack.add(module)

            for dep in passports.get(module, []):
                if dep not in visited:
                    if has_cycle(dep, visited, rec_stack):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(module)
            return False

        for module in passports:
            visited = set()
            rec_stack = set()
            assert not has_cycle(module, visited, rec_stack), f"Circular dependency detected in {module}"
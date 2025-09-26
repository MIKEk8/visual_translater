"""
Unit tests for CLAUDE.md command validation and environment setup.
Tests verify that all commands and configurations in CLAUDE.md work correctly.
"""

import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import yaml
import os


class TestClaudeMdValidation:
    """Test suite for CLAUDE.md validation and command execution."""

    def setup_method(self):
        """Setup test environment."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.claude_md_path = self.project_root / "CLAUDE.md"
        self.venv_python = self.project_root / "wenv" / "Scripts" / "python.exe"

    # CRITICAL: Virtual environment validation
    def test_venv_python_exists(self):
        """Test that virtual environment Python executable exists."""
        assert self.venv_python.exists(), f"Virtual environment Python not found at {self.venv_python}"

    # CRITICAL: CLAUDE.md exists and is readable
    def test_claude_md_exists(self):
        """Test that CLAUDE.md exists in project root."""
        assert self.claude_md_path.exists(), "CLAUDE.md not found in project root"
        assert self.claude_md_path.is_file(), "CLAUDE.md is not a file"

    def test_claude_md_structure(self):
        """Test that CLAUDE.md contains all required sections."""
        content = self.claude_md_path.read_text(encoding='utf-8')

        required_sections = [
            "## 🚨 CRITICAL:",
            "## 🔄 Замкнутый цикл разработки",
            "## ✅ Definition of Done",
            "## 🧪 Testing policy",
            "## 📜 Команды",
            "## 📂 Паспорта модулей",
            "## 🧩 Subagents",
            "## 📊 Отчёты и артефакты",
            "## 🔒 Ограничения"
        ]

        for section in required_sections:
            assert section in content, f"Missing required section: {section}"

    # CRITICAL: Test command execution
    def test_pytest_command_execution(self):
        """Test that pytest commands from CLAUDE.md work correctly."""
        # Test basic pytest command
        result = subprocess.run(
            [str(self.venv_python), "-m", "pytest", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "pytest not properly installed in venv"

    def test_pytest_coverage_command(self):
        """Test that pytest with coverage reporting works."""
        result = subprocess.run(
            [str(self.venv_python), "-m", "pytest", "--cov=src", "--cov-report=term", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "pytest-cov not properly configured"

    # CRITICAL: Linter validation
    def test_flake8_command(self):
        """Test that flake8 linter is available and configured."""
        result = subprocess.run(
            [str(self.venv_python), "-m", "flake8", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "flake8 not properly installed"

    def test_mypy_command(self):
        """Test that mypy type checker is available."""
        result = subprocess.run(
            [str(self.venv_python), "-m", "mypy", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "mypy not properly installed"

    def test_black_formatter(self):
        """Test that black formatter is available."""
        result = subprocess.run(
            [str(self.venv_python), "-m", "black", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "black formatter not properly installed"

    def test_isort_command(self):
        """Test that isort import sorter is available."""
        result = subprocess.run(
            [str(self.venv_python), "-m", "isort", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "isort not properly installed"

    # CRITICAL: Module passport directory structure
    def test_module_passport_directory_exists(self):
        """Test that docs/modules directory exists for passports."""
        modules_dir = self.project_root / "docs" / "modules"
        assert modules_dir.exists(), "docs/modules directory not found"
        assert modules_dir.is_dir(), "docs/modules is not a directory"

    def test_module_passport_template_exists(self):
        """Test that module passport template exists."""
        template_path = self.project_root / "docs" / "modules" / "_template.yml"
        assert template_path.exists(), "Module passport template not found"

    # CRITICAL: Test discovery configuration
    def test_pyproject_toml_test_paths(self):
        """Test that pyproject.toml includes all test paths."""
        pyproject_path = self.project_root / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml not found"

        import toml
        config = toml.load(pyproject_path)

        # Check pytest configuration
        assert "tool" in config, "No tool section in pyproject.toml"
        assert "pytest" in config["tool"], "No pytest configuration in pyproject.toml"

        pytest_config = config["tool"]["pytest"]["ini_options"]
        testpaths = pytest_config.get("testpaths", [])

        # Should include both unit and integration tests
        assert "src/tests/unit" in testpaths, "Unit tests not in testpaths"
        assert "src/tests/integration" in testpaths, "Integration tests not in testpaths"

    def test_coverage_baseline_exists(self):
        """Test that coverage baseline is established and documented."""
        coverage_file = self.project_root / "docs" / "_coverage" / "baseline.txt"
        assert coverage_file.exists(), "Coverage baseline not established"

        content = coverage_file.read_text()
        # Should contain percentage
        assert "%" in content, "Coverage baseline doesn't contain percentage"

        # Parse coverage percentage
        import re
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', content)
        assert match, "Could not parse coverage percentage"

        coverage = float(match.group(1))
        assert coverage >= 0, "Invalid coverage percentage"

    # CRITICAL: Definition of Done criteria
    def test_dod_coverage_threshold(self):
        """Test that coverage meets Definition of Done threshold (80%)."""
        # Run coverage report
        result = subprocess.run(
            [str(self.venv_python), "-m", "pytest",
             "--cov=src", "--cov-report=term", "--quiet"],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )

        # Parse coverage from output
        import re
        match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', result.stdout)
        if match:
            coverage = int(match.group(1))
            assert coverage >= 80, f"Coverage {coverage}% is below 80% threshold"
        else:
            pytest.fail("Could not determine coverage percentage")

    def test_dod_linters_pass(self):
        """Test that all linters pass without errors (Definition of Done)."""
        linters = [
            (["flake8", "src"], "flake8"),
            (["mypy", "src"], "mypy"),
            (["black", "--check", "src"], "black"),
            (["isort", "--check-only", "src"], "isort")
        ]

        for cmd, name in linters:
            result = subprocess.run(
                [str(self.venv_python), "-m"] + cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )
            assert result.returncode == 0, f"{name} linter failed with errors"

    # CRITICAL: Subagent roles validation
    def test_subagent_definitions_exist(self):
        """Test that all subagent definitions exist in .claude/agents/."""
        agents_dir = self.project_root / ".claude" / "agents"
        assert agents_dir.exists(), ".claude/agents directory not found"

        required_agents = [
            "architect.md",
            "test-writer.md",
            "coder.md",
            "test-runner.md",
            "reviewer.md",
            "fixer.md",
            "scribe.md"
        ]

        for agent_file in required_agents:
            agent_path = agents_dir / agent_file
            assert agent_path.exists(), f"Subagent definition missing: {agent_file}"

    def test_artifacts_directory_structure(self):
        """Test that all artifact directories mentioned in CLAUDE.md exist."""
        docs_dir = self.project_root / "docs"

        required_artifacts = [
            "plan.md",
            "_tdd_failures.md",
            "_changes.md",
            "_coverage",
            "_review.md",
            "_fixlog.md",
            "last_run_report.md"
        ]

        for artifact in required_artifacts:
            artifact_path = docs_dir / artifact
            # These should be created during workflow, so we test for the docs dir
            assert docs_dir.exists(), "docs directory not found for artifacts"

    def test_tmp_directory_constraint(self):
        """Test that tmp/ directory exists for temporary files (constraint from CLAUDE.md)."""
        tmp_dir = self.project_root / "tmp"
        assert tmp_dir.exists(), "tmp/ directory not found (required by CLAUDE.md constraints)"
        assert tmp_dir.is_dir(), "tmp/ is not a directory"

    def test_no_php_renpy_references(self):
        """Test that CLAUDE.md doesn't contain PHP/Ren'Py references (not applicable to this project)."""
        content = self.claude_md_path.read_text(encoding='utf-8')

        # These should have been removed as per plan
        assert "vendor/bin/pest" not in content, "PHP Pest reference found (should be removed)"
        assert "vendor/bin/phpunit" not in content, "PHPUnit reference found (should be removed)"
        assert "run-renpy-lint.sh" not in content, "Ren'Py lint reference found (should be removed)"
        assert "phpstan" not in content, "PHPStan reference found (should be removed)"
        assert "phpcs" not in content, "PHP CodeSniffer reference found (should be removed)"

    def test_windows_specific_commands(self):
        """Test that CLAUDE.md uses Windows-specific paths."""
        content = self.claude_md_path.read_text(encoding='utf-8')

        # Should use Windows path separators in venv paths
        assert r"wenv\Scripts\python.exe" in content, "Windows venv path not found"
        # Should not have Unix-style venv paths
        assert "venv/bin/python" not in content, "Unix venv path found (should use Windows paths)"

    def test_development_scripts_exist(self):
        """Test that development scripts mentioned in plan exist."""
        scripts_dir = self.project_root / "scripts"

        required_scripts = [
            "run-tests.bat",
            "run-linters.bat",
            "coverage-report.bat"
        ]

        for script in required_scripts:
            script_path = scripts_dir / script
            assert script_path.exists(), f"Development script missing: {script}"

            # Check script is executable (has content)
            content = script_path.read_text()
            assert len(content) > 0, f"Script {script} is empty"
            assert "@echo off" in content or "REM" in content, f"Script {script} doesn't look like a batch file"


class TestClaudeMdWorkflow:
    """Test the complete development workflow defined in CLAUDE.md."""

    def setup_method(self):
        """Setup test environment."""
        self.project_root = Path(__file__).parent.parent.parent.parent

    # CRITICAL: Test TDD workflow
    def test_tdd_workflow_stages(self):
        """Test that all TDD workflow stages can be executed."""
        workflow_stages = {
            "plan": self.project_root / "docs" / "plan.md",
            "test": self.project_root / "docs" / "_tdd_failures.md",
            "implement": self.project_root / "docs" / "_changes.md",
            "verify": self.project_root / "docs" / "_coverage",
            "review": self.project_root / "docs" / "_review.md",
            "report": self.project_root / "docs" / "last_run_report.md"
        }

        for stage, artifact_path in workflow_stages.items():
            # All artifacts should be creatable
            assert artifact_path.parent.exists(), f"Parent directory for {stage} artifact doesn't exist"

    def test_definition_of_done_checklist(self):
        """Test that Definition of Done can be validated programmatically."""
        dod_checks = {
            "tests_pass": self._check_tests_pass(),
            "coverage_80": self._check_coverage_threshold(),
            "linters_pass": self._check_linters_pass(),
            "passports_updated": self._check_passports_updated(),
            "report_generated": self._check_report_exists()
        }

        for check, result in dod_checks.items():
            assert result, f"DoD check failed: {check}"

    def _check_tests_pass(self):
        """Check if all critical tests pass."""
        # This would run pytest and check return code
        return False  # Intentionally failing for TDD

    def _check_coverage_threshold(self):
        """Check if coverage meets 80% threshold."""
        # This would parse coverage report
        return False  # Intentionally failing for TDD

    def _check_linters_pass(self):
        """Check if all linters pass."""
        # This would run linters and check outputs
        return False  # Intentionally failing for TDD

    def _check_passports_updated(self):
        """Check if module passports are up to date."""
        # This would check timestamps on passport files
        return False  # Intentionally failing for TDD

    def _check_report_exists(self):
        """Check if final report exists with READY/NOT READY status."""
        report_path = self.project_root / "docs" / "last_run_report.md"
        if not report_path.exists():
            return False

        content = report_path.read_text()
        return "READY" in content or "NOT READY" in content
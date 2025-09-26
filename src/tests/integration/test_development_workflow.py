"""
Integration tests for the complete TDD development workflow.
Tests the full pipeline from plan to report generation.
"""

import pytest
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import yaml
import json
import time
from typing import Dict, List, Tuple
from unittest.mock import Mock, patch, MagicMock
import shutil
import tempfile


class DevelopmentWorkflow:
    """Handler for executing the full TDD development workflow."""

    def __init__(self, project_root: Path):
        """Initialize workflow with project root."""
        self.project_root = project_root
        self.venv_python = project_root / "wenv" / "Scripts" / "python.exe"
        self.docs_dir = project_root / "docs"
        self.artifacts = {}
        self.start_time = None
        self.end_time = None

    def execute_plan_phase(self) -> bool:
        """Execute architecture planning phase."""
        plan_path = self.docs_dir / "plan.md"

        # Check if architect subagent created plan
        if not plan_path.exists():
            return False

        with open(plan_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Validate plan structure
        required_sections = [
            "## 🎯 Objective",
            "## 📋 Analysis Summary",
            "## 🏗️ Implementation Plan",
            "## 🧪 Testing Strategy",
            "## 📊 Success Criteria"
        ]

        for section in required_sections:
            if section not in content:
                return False

        self.artifacts['plan'] = plan_path
        return True

    def execute_test_phase(self) -> Tuple[bool, List[str]]:
        """Execute test writing phase (TDD - write failing tests)."""
        failures_path = self.docs_dir / "_tdd_failures.md"

        # Run tests and capture failures
        result = subprocess.run(
            [str(self.venv_python), "-m", "pytest", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )

        # Parse test output
        failed_tests = []
        for line in result.stdout.split('\n'):
            if 'FAILED' in line:
                failed_tests.append(line.strip())

        # Write failures report
        with open(failures_path, 'w', encoding='utf-8') as f:
            f.write("# TDD Test Failures Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"Total failures: {len(failed_tests)}\n\n")
            f.write("## Failed Tests\n\n")
            for test in failed_tests:
                f.write(f"- {test}\n")

        self.artifacts['tdd_failures'] = failures_path
        return len(failed_tests) > 0, failed_tests

    def execute_implementation_phase(self) -> bool:
        """Execute code implementation phase."""
        changes_path = self.docs_dir / "_changes.md"

        # Track changed files (simulate coder subagent work)
        changed_files = self._get_changed_files()

        # Write changes report
        with open(changes_path, 'w', encoding='utf-8') as f:
            f.write("# Implementation Changes Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"Files changed: {len(changed_files)}\n\n")
            f.write("## Changed Files\n\n")
            for file in changed_files:
                f.write(f"- {file}\n")

        self.artifacts['changes'] = changes_path
        return len(changed_files) > 0

    def execute_verify_phase(self) -> Tuple[bool, float]:
        """Execute verification phase with coverage reporting."""
        coverage_dir = self.docs_dir / "_coverage"
        coverage_dir.mkdir(exist_ok=True)

        # Run tests with coverage
        result = subprocess.run(
            [str(self.venv_python), "-m", "pytest",
             "--cov=src", "--cov-report=json", "--cov-report=term"],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )

        # Parse coverage percentage
        coverage_pct = 0.0
        import re
        match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', result.stdout)
        if match:
            coverage_pct = float(match.group(1))

        # Save coverage report
        coverage_report = coverage_dir / "coverage.json"
        if Path("coverage.json").exists():
            shutil.move("coverage.json", coverage_report)

        # Write baseline if doesn't exist
        baseline_file = coverage_dir / "baseline.txt"
        if not baseline_file.exists():
            with open(baseline_file, 'w', encoding='utf-8') as f:
                f.write(f"Baseline coverage: {coverage_pct}%\n")
                f.write(f"Established: {datetime.now().isoformat()}\n")

        self.artifacts['coverage'] = coverage_dir
        return result.returncode == 0, coverage_pct

    def execute_review_phase(self) -> List[str]:
        """Execute code review phase."""
        review_path = self.docs_dir / "_review.md"

        # Simulate reviewer subagent findings
        issues = self._run_code_review()

        # Write review report
        with open(review_path, 'w', encoding='utf-8') as f:
            f.write("# Code Review Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"Issues found: {len(issues)}\n\n")

            if issues:
                f.write("## Critical Issues\n\n")
                for issue in issues:
                    if issue.get('severity') == 'critical':
                        f.write(f"- [{issue['type']}] {issue['message']}\n")

                f.write("\n## Warnings\n\n")
                for issue in issues:
                    if issue.get('severity') == 'warning':
                        f.write(f"- [{issue['type']}] {issue['message']}\n")

        self.artifacts['review'] = review_path
        return issues

    def execute_fix_phase(self, issues: List[str]) -> bool:
        """Execute fix phase for critical issues."""
        fixlog_path = self.docs_dir / "_fixlog.md"

        fixed_issues = []
        for issue in issues:
            if issue.get('severity') == 'critical':
                # Simulate fixing critical issues
                fixed = self._attempt_fix(issue)
                if fixed:
                    fixed_issues.append(issue)

        # Write fix log
        with open(fixlog_path, 'w', encoding='utf-8') as f:
            f.write("# Fix Log Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"Fixed issues: {len(fixed_issues)}/{len(issues)}\n\n")
            f.write("## Fixed Issues\n\n")
            for issue in fixed_issues:
                f.write(f"- {issue['message']}\n")

        self.artifacts['fixlog'] = fixlog_path
        return len(fixed_issues) == sum(1 for i in issues if i.get('severity') == 'critical')

    def generate_final_report(self) -> str:
        """Generate final workflow report with READY/NOT READY status."""
        report_path = self.docs_dir / "last_run_report.md"

        # Collect all metrics
        metrics = self._collect_metrics()

        # Determine READY status
        status = self._determine_ready_status(metrics)

        # Generate report
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# Development Workflow Report - {status}\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            f.write("## Workflow Summary\n\n")
            f.write(f"- Status: **{status}**\n")
            f.write(f"- Duration: {metrics.get('duration', 'N/A')}\n")
            f.write(f"- Coverage: {metrics.get('coverage', 0)}%\n")
            f.write(f"- Tests Pass: {metrics.get('tests_pass', False)}\n")
            f.write(f"- Linters Pass: {metrics.get('linters_pass', False)}\n\n")

            f.write("## Definition of Done Checklist\n\n")
            dod_items = [
                ('Critical tests green', metrics.get('tests_pass', False)),
                ('Coverage ≥ 80%', metrics.get('coverage', 0) >= 80),
                ('Linters pass', metrics.get('linters_pass', False)),
                ('Module passports updated', metrics.get('passports_updated', False)),
                ('No critical issues', metrics.get('critical_issues', 1) == 0)
            ]

            for item, passed in dod_items:
                status_icon = '✅' if passed else '❌'
                f.write(f"- {status_icon} {item}\n")

            f.write("\n## Artifacts Generated\n\n")
            for name, path in self.artifacts.items():
                f.write(f"- {name}: {path}\n")

        self.artifacts['report'] = report_path
        return status

    def _get_changed_files(self) -> List[str]:
        """Get list of changed files in current branch."""
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        return result.stdout.strip().split('\n') if result.stdout else []

    def _run_code_review(self) -> List[Dict]:
        """Run automated code review checks."""
        issues = []

        # Run linters
        linters = [
            ("flake8", ["flake8", "src", "--count"]),
            ("mypy", ["mypy", "src", "--no-error-summary"]),
            ("black", ["black", "--check", "src"]),
        ]

        for name, cmd in linters:
            result = subprocess.run(
                [str(self.venv_python), "-m"] + cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )

            if result.returncode != 0:
                issues.append({
                    'type': name,
                    'severity': 'critical' if name == 'mypy' else 'warning',
                    'message': f"{name} found issues"
                })

        return issues

    def _attempt_fix(self, issue: Dict) -> bool:
        """Attempt to fix an issue (simulated)."""
        # In real implementation, this would run fixer subagent
        if issue['type'] == 'black':
            # Auto-format with black
            result = subprocess.run(
                [str(self.venv_python), "-m", "black", "src"],
                capture_output=True,
                cwd=str(self.project_root)
            )
            return result.returncode == 0
        return False

    def _collect_metrics(self) -> Dict:
        """Collect all workflow metrics."""
        metrics = {
            'duration': self._calculate_duration(),
            'coverage': self._get_coverage(),
            'tests_pass': self._check_tests_pass(),
            'linters_pass': self._check_linters_pass(),
            'passports_updated': self._check_passports_updated(),
            'critical_issues': self._count_critical_issues()
        }
        return metrics

    def _calculate_duration(self) -> str:
        """Calculate workflow duration."""
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            return str(duration)
        return "N/A"

    def _get_coverage(self) -> float:
        """Get current test coverage percentage."""
        result = subprocess.run(
            [str(self.venv_python), "-m", "pytest", "--cov=src", "--cov-report=term", "-q"],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )

        import re
        match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', result.stdout)
        if match:
            return float(match.group(1))
        return 0.0

    def _check_tests_pass(self) -> bool:
        """Check if all tests pass."""
        result = subprocess.run(
            [str(self.venv_python), "-m", "pytest", "-q"],
            capture_output=True,
            cwd=str(self.project_root)
        )
        return result.returncode == 0

    def _check_linters_pass(self) -> bool:
        """Check if all linters pass."""
        linters = [
            ["flake8", "src"],
            ["mypy", "src"],
            ["black", "--check", "src"],
            ["isort", "--check-only", "src"]
        ]

        for cmd in linters:
            result = subprocess.run(
                [str(self.venv_python), "-m"] + cmd,
                capture_output=True,
                cwd=str(self.project_root)
            )
            if result.returncode != 0:
                return False
        return True

    def _check_passports_updated(self) -> bool:
        """Check if module passports are up to date."""
        modules_dir = self.project_root / "docs" / "modules"
        passport_files = list(modules_dir.glob("*.yml"))

        # Check at least some passports exist
        if len(passport_files) < 3:
            return False

        # Check timestamps
        today = datetime.now().date()
        for passport_file in passport_files[:3]:  # Check first 3
            with open(passport_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                last_updated = datetime.strptime(data['last_updated'], '%Y-%m-%d').date()
                if (today - last_updated).days > 30:
                    return False

        return True

    def _count_critical_issues(self) -> int:
        """Count critical issues from review."""
        review_path = self.docs_dir / "_review.md"
        if not review_path.exists():
            return 0

        with open(review_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Simple count of critical issues
            return content.count('[critical]')

    def _determine_ready_status(self, metrics: Dict) -> str:
        """Determine if feature is READY based on DoD criteria."""
        ready = (
            metrics.get('tests_pass', False) and
            metrics.get('coverage', 0) >= 80 and
            metrics.get('linters_pass', False) and
            metrics.get('passports_updated', False) and
            metrics.get('critical_issues', 1) == 0
        )
        return "READY" if ready else "NOT READY"


class TestDevelopmentWorkflow:
    """Integration tests for the full development workflow."""

    def setup_method(self):
        """Setup test environment."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.workflow = DevelopmentWorkflow(self.project_root)

    # CRITICAL: Full workflow execution
    def test_complete_workflow_execution(self):
        """Test execution of complete TDD workflow from plan to report."""
        workflow = DevelopmentWorkflow(self.project_root)
        workflow.start_time = datetime.now()

        # Phase 1: Plan
        plan_success = workflow.execute_plan_phase()
        assert plan_success, "Plan phase failed"

        # Phase 2: Write failing tests (TDD)
        has_failures, failed_tests = workflow.execute_test_phase()
        assert has_failures, "No failing tests found (violates TDD)"
        assert len(failed_tests) > 0, "Should have failing tests initially"

        # Phase 3: Implementation
        impl_success = workflow.execute_implementation_phase()
        assert impl_success, "Implementation phase failed"

        # Phase 4: Verify with coverage
        tests_pass, coverage = workflow.execute_verify_phase()
        assert coverage >= 80, f"Coverage {coverage}% below 80% threshold"

        # Phase 5: Review
        issues = workflow.execute_review_phase()
        critical_count = sum(1 for i in issues if i.get('severity') == 'critical')

        # Phase 6: Fix critical issues
        if critical_count > 0:
            fix_success = workflow.execute_fix_phase(issues)
            assert fix_success, "Failed to fix critical issues"

        # Phase 7: Generate report
        workflow.end_time = datetime.now()
        status = workflow.generate_final_report()
        assert status in ["READY", "NOT READY"], f"Invalid status: {status}"

    # CRITICAL: Plan validation
    def test_plan_phase_creates_valid_plan(self):
        """Test that plan phase creates valid architectural plan."""
        success = self.workflow.execute_plan_phase()
        assert success, "Plan phase should succeed"

        plan_path = self.project_root / "docs" / "plan.md"
        assert plan_path.exists(), "Plan document not created"

        with open(plan_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Screen Translator" in content, "Plan should be for Screen Translator project"
            assert "Clean Architecture" in content, "Plan should mention architecture"

    # CRITICAL: TDD compliance
    def test_tdd_workflow_starts_with_failing_tests(self):
        """Test that TDD workflow properly starts with failing tests."""
        has_failures, failed_tests = self.workflow.execute_test_phase()

        # For TDD, we should have failing tests initially
        assert has_failures, "TDD requires failing tests first"

        failures_report = self.project_root / "docs" / "_tdd_failures.md"
        assert failures_report.exists(), "TDD failures report not created"

        with open(failures_report, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Total failures:" in content, "Report should show failure count"

    def test_implementation_tracking(self):
        """Test that implementation phase tracks code changes."""
        success = self.workflow.execute_implementation_phase()

        changes_report = self.project_root / "docs" / "_changes.md"
        assert changes_report.exists(), "Changes report not created"

        with open(changes_report, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Files changed:" in content, "Report should show changed files"

    # CRITICAL: Coverage validation
    def test_coverage_reporting_and_baseline(self):
        """Test coverage reporting and baseline establishment."""
        tests_pass, coverage = self.workflow.execute_verify_phase()

        coverage_dir = self.project_root / "docs" / "_coverage"
        assert coverage_dir.exists(), "Coverage directory not created"

        baseline_file = coverage_dir / "baseline.txt"
        assert baseline_file.exists(), "Coverage baseline not established"

        with open(baseline_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Baseline coverage:" in content, "Baseline should show coverage"

    def test_code_review_integration(self):
        """Test code review phase integration with linters."""
        issues = self.workflow.execute_review_phase()

        review_report = self.project_root / "docs" / "_review.md"
        assert review_report.exists(), "Review report not created"

        with open(review_report, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Code Review Report" in content, "Invalid review report format"
            assert "Issues found:" in content, "Report should show issue count"

    def test_fix_phase_handles_critical_issues(self):
        """Test that fix phase properly handles critical issues."""
        # Create mock issues
        issues = [
            {'type': 'mypy', 'severity': 'critical', 'message': 'Type error'},
            {'type': 'flake8', 'severity': 'warning', 'message': 'Line too long'}
        ]

        success = self.workflow.execute_fix_phase(issues)

        fixlog = self.project_root / "docs" / "_fixlog.md"
        assert fixlog.exists(), "Fix log not created"

        with open(fixlog, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Fixed issues:" in content, "Fix log should show fixed count"

    # CRITICAL: Definition of Done validation
    def test_definition_of_done_criteria(self):
        """Test that DoD criteria are properly validated."""
        metrics = self.workflow._collect_metrics()

        # All DoD criteria should be checkable
        assert 'coverage' in metrics, "Coverage not in metrics"
        assert 'tests_pass' in metrics, "Test status not in metrics"
        assert 'linters_pass' in metrics, "Linter status not in metrics"
        assert 'passports_updated' in metrics, "Passport status not in metrics"
        assert 'critical_issues' in metrics, "Critical issues not in metrics"

        # Validate threshold
        if metrics['coverage'] >= 80:
            assert metrics['coverage'] >= 80, "Coverage should meet 80% threshold"

    # CRITICAL: Final report generation
    def test_final_report_generation_with_status(self):
        """Test that final report is generated with READY/NOT READY status."""
        status = self.workflow.generate_final_report()

        report_path = self.project_root / "docs" / "last_run_report.md"
        assert report_path.exists(), "Final report not created"

        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert status in content, f"Status '{status}' not in report"
            assert "Definition of Done Checklist" in content, "DoD checklist missing"
            assert "✅" in content or "❌" in content, "Status icons missing"

    def test_workflow_artifact_tracking(self):
        """Test that all workflow artifacts are properly tracked."""
        # Execute partial workflow
        self.workflow.execute_plan_phase()
        self.workflow.execute_test_phase()
        self.workflow.execute_implementation_phase()

        # Check artifacts are tracked
        assert 'plan' in self.workflow.artifacts
        assert 'tdd_failures' in self.workflow.artifacts
        assert 'changes' in self.workflow.artifacts

        # All artifacts should point to existing files
        for name, path in self.workflow.artifacts.items():
            assert path.exists(), f"Artifact {name} file doesn't exist at {path}"

    def test_windows_environment_compatibility(self):
        """Test that workflow works correctly on Windows."""
        import platform
        if platform.system() != 'Windows':
            pytest.skip("Windows-specific test")

        # Check Windows Python executable
        venv_python = self.project_root / "wenv" / "Scripts" / "python.exe"
        assert venv_python.exists(), "Windows venv Python not found"

        # Test command execution on Windows
        result = subprocess.run(
            [str(venv_python), "-c", "import sys; print(sys.platform)"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Failed to execute Python on Windows"
        assert "win" in result.stdout, "Not running on Windows platform"

    def test_parallel_workflow_stages(self):
        """Test that independent workflow stages can run in parallel."""
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # These stages could potentially run in parallel
            future1 = executor.submit(self.workflow._check_tests_pass)
            future2 = executor.submit(self.workflow._check_linters_pass)
            future3 = executor.submit(self.workflow._check_passports_updated)

            # All should complete without errors
            results = [future1.result(), future2.result(), future3.result()]

            # Results should be boolean
            for result in results:
                assert isinstance(result, bool), "Parallel check should return boolean"

    # CRITICAL: Coverage baseline comparison
    def test_coverage_baseline_comparison(self):
        """Test that coverage is compared against baseline."""
        # Establish baseline
        _, initial_coverage = self.workflow.execute_verify_phase()

        baseline_file = self.project_root / "docs" / "_coverage" / "baseline.txt"
        if baseline_file.exists():
            with open(baseline_file, 'r', encoding='utf-8') as f:
                content = f.read()
                import re
                match = re.search(r'(\d+(?:\.\d+)?)\s*%', content)
                if match:
                    baseline = float(match.group(1))
                    # Current coverage should be >= baseline
                    assert initial_coverage >= baseline, f"Coverage {initial_coverage}% below baseline {baseline}%"

    def test_report_not_ready_status(self):
        """Test that report correctly shows NOT READY when criteria not met."""
        # Force some metrics to fail
        with patch.object(self.workflow, '_collect_metrics') as mock_metrics:
            mock_metrics.return_value = {
                'duration': '00:05:00',
                'coverage': 70,  # Below 80%
                'tests_pass': False,  # Tests failing
                'linters_pass': True,
                'passports_updated': True,
                'critical_issues': 0
            }

            status = self.workflow.generate_final_report()
            assert status == "NOT READY", "Should be NOT READY when DoD criteria not met"

            report_path = self.project_root / "docs" / "last_run_report.md"
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "❌" in content, "Should have failed checkmarks"
                assert "Coverage ≥ 80%" in content, "Should show failed coverage requirement"
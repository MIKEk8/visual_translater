import unittest
from pathlib import Path

from build import run_security_scan


class SecurityScanTest(unittest.TestCase):
    """Tests for the run_security_scan helper."""

    def test_bandit_violation_causes_failure(self):
        """run_security_scan should return False when Bandit finds issues."""
        vuln_file = Path("src") / "vuln_example.py"
        vuln_file.write_text("def bad():\n    eval('1+1')\n")
        try:
            result = run_security_scan()
            self.assertFalse(result)
        finally:
            if vuln_file.exists():
                vuln_file.unlink()

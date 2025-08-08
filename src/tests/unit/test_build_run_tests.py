import pytest
from unittest.mock import patch
import subprocess
import build


def test_run_tests_passes_workers_option():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        build.run_tests(workers='auto')
        cmd = mock_run.call_args[0][0]
    assert '-n' in cmd
    assert 'auto' in cmd

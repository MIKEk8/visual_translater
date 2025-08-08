#!/usr/bin/env python3
"""
Code quality check runner for Screen Translator project.
Runs multiple static analysis tools and generates reports.
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import List, Tuple, Dict
import json
import time
import platform


class QualityChecker:
    """Run various code quality checks and report results"""
    
    def __init__(self, src_path: str = "src"):
        self.src_path = Path(src_path)
        self.reports_dir = Path("quality_reports")
        self.reports_dir.mkdir(exist_ok=True)
        self.results: Dict[str, Tuple[bool, str]] = {}
        
        # Determine the command prefix based on virtual environment
        self.cmd_prefix = []
        
        # Check if environment info was passed from build.py (optimized)
        env_type = os.environ.get("SCREEN_TRANSLATOR_PYTHON_ENV")
        python_exe_path = os.environ.get("SCREEN_TRANSLATOR_PYTHON_EXE")
        
        if env_type and python_exe_path:
            # Use pre-determined environment info (avoids redundant detection)
            self.cmd_prefix = [python_exe_path, "-m"]
            print(f"Using {env_type.upper()} environment (from build.py): {python_exe_path}")
        else:
            # Fallback to auto-detection (for direct script calls)
            # Check for wenv first (Windows Environment - preferred on Windows)
            if os.path.exists("wenv") and platform.system() == "Windows":
                python_exe = Path("wenv") / "Scripts" / "python.exe"
                if python_exe.exists():
                    self.cmd_prefix = [str(python_exe), "-m"]
                    print(f"Using Windows Environment (wenv): {python_exe}")
            # Check for .venv (legacy or Linux/macOS)
            elif os.path.exists(".venv"):
                if platform.system() == "Windows":
                    python_exe = Path(".venv") / "Scripts" / "python.exe"
                else:
                    python_exe = Path(".venv") / "bin" / "python"
                if python_exe.exists():
                    self.cmd_prefix = [str(python_exe), "-m"]
                    print(f"Using Virtual Environment (.venv): {python_exe}")
            else:
                print("No virtual environment found, using system Python")
        
    def run_command(self, cmd: List[str], name: str) -> Tuple[bool, str]:
        """Run a command and capture output"""
        print(f"\n{'='*60}")
        print(f"Running {name}...")
        print(f"Command: {' '.join(cmd)}")
        print(f"{'='*60}")
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            output = result.stdout + result.stderr
            success = result.returncode == 0
            
            # Save output to file
            output_file = self.reports_dir / f"{name.lower().replace(' ', '_')}.txt"
            output_file.write_text(output, encoding='utf-8')
            
            if success:
                print(f"✅ {name} passed!")
            else:
                print(f"❌ {name} failed with return code {result.returncode}")
                print("Output preview:")
                print(output[:500] + "..." if len(output) > 500 else output)
                
            return success, output
            
        except Exception as e:
            error_msg = f"Error running {name}: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def check_black(self):
        """Check code formatting with Black"""
        cmd = self.cmd_prefix + ["black", "--check", "--diff", str(self.src_path)]
        return self.run_command(cmd, "Black (Code Formatting)")
    
    def check_isort(self):
        """Check import sorting with isort"""
        cmd = self.cmd_prefix + ["isort", "--check-only", "--diff", str(self.src_path)]
        return self.run_command(cmd, "isort (Import Sorting)")
    
    def check_flake8(self):
        """Check code style with Flake8"""
        cmd = self.cmd_prefix + ["flake8", str(self.src_path)]
        return self.run_command(cmd, "Flake8 (Style Guide)")
    
    def check_pylint(self):
        """Check code quality with Pylint"""
        cmd = self.cmd_prefix + ["pylint", str(self.src_path)]
        return self.run_command(cmd, "Pylint (Code Quality)")
    
    def check_mypy(self):
        """Check type hints with MyPy"""
        cmd = self.cmd_prefix + ["mypy", str(self.src_path)]
        return self.run_command(cmd, "MyPy (Type Checking)")
    
    def check_bandit(self):
        """Check security issues with Bandit"""
        cmd = self.cmd_prefix + ["bandit", "-r", str(self.src_path), "-f", "txt"]
        return self.run_command(cmd, "Bandit (Security)")
    
    def check_vulture(self):
        """Check for dead code with Vulture"""
        cmd = self.cmd_prefix + ["vulture", str(self.src_path), "--min-confidence", "80"]
        return self.run_command(cmd, "Vulture (Dead Code)")
    
    def check_radon_cc(self):
        """Check cyclomatic complexity with Radon"""
        cmd = self.cmd_prefix + ["radon", "cc", str(self.src_path), "-a", "-nc"]
        return self.run_command(cmd, "Radon (Cyclomatic Complexity)")
    
    def check_radon_mi(self):
        """Check maintainability index with Radon"""
        cmd = self.cmd_prefix + ["radon", "mi", str(self.src_path), "-n", "B"]
        return self.run_command(cmd, "Radon (Maintainability Index)")
    
    def check_pydocstyle(self):
        """Check docstring style with pydocstyle"""
        cmd = self.cmd_prefix + ["pydocstyle", str(self.src_path)]
        return self.run_command(cmd, "Pydocstyle (Docstring Style)")
    
    def check_safety(self):
        """Check for known security vulnerabilities in dependencies"""
        cmd = self.cmd_prefix + ["safety", "check", "--json"]
        success, output = self.run_command(cmd, "Safety (Dependency Security)")
        
        # Parse JSON output for better display
        try:
            if output.strip():
                vulnerabilities = json.loads(output)
                if vulnerabilities:
                    print("\n⚠️  Security vulnerabilities found:")
                    for vuln in vulnerabilities:
                        print(f"  - {vuln.get('package', 'Unknown')}: {vuln.get('vulnerability', 'Unknown issue')}")
        except:
            pass
            
        return success, output
    
    def check_prospector(self):
        """Run Prospector meta-linter combining multiple tools"""
        cmd = self.cmd_prefix + ["prospector", str(self.src_path), "--output-format", "grouped", "--strictness", "medium"]
        return self.run_command(cmd, "Prospector (Meta-linter)")
    
    def run_all_checks(self):
        """Run all quality checks"""
        print("\n" + "="*80)
        print("🔍 STARTING CODE QUALITY CHECKS FOR SCREEN TRANSLATOR")
        print("="*80)
        
        start_time = time.time()
        
        # Define checks to run
        checks = [
            ("Black", self.check_black),
            ("isort", self.check_isort),
            ("Flake8", self.check_flake8),
            ("MyPy", self.check_mypy),
            ("Pylint", self.check_pylint),
            ("Bandit", self.check_bandit),
            ("Vulture", self.check_vulture),
            ("Radon CC", self.check_radon_cc),
            ("Radon MI", self.check_radon_mi),
            ("Pydocstyle", self.check_pydocstyle),
            ("Safety", self.check_safety),
            ("Prospector", self.check_prospector),
        ]
        
        # Run checks
        for name, check_func in checks:
            try:
                success, output = check_func()
                self.results[name] = (success, output)
            except Exception as e:
                self.results[name] = (False, str(e))
        
        # Generate summary
        self.generate_summary()
        
        elapsed_time = time.time() - start_time
        print(f"\n⏱️  Total time: {elapsed_time:.2f} seconds")
        
        # Return overall success
        return all(success for success, _ in self.results.values())
    
    def generate_summary(self):
        """Generate and display summary of all checks"""
        print("\n" + "="*80)
        print("📊 QUALITY CHECK SUMMARY")
        print("="*80)
        
        passed = 0
        failed = 0
        
        for name, (success, _) in self.results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{name:.<40} {status}")
            if success:
                passed += 1
            else:
                failed += 1
        
        print("="*80)
        print(f"Total: {len(self.results)} checks")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        
        # Save summary to JSON
        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_checks": len(self.results),
            "passed": passed,
            "failed": failed,
            "results": {
                name: {"success": success, "output_file": f"{name.lower().replace(' ', '_')}.txt"}
                for name, (success, _) in self.results.items()
            }
        }
        
        summary_file = self.reports_dir / "summary.json"
        summary_file.write_text(json.dumps(summary, indent=2), encoding='utf-8')
        
        print(f"\n📁 Detailed reports saved to: {self.reports_dir.absolute()}")
        
        if failed > 0:
            print("\n⚠️  Some checks failed. Please review the reports for details.")
            print("💡 Tip: You can auto-fix some issues with:")
            print("   - black src/        # Format code")
            print("   - isort src/        # Sort imports")


def main():
    """Main entry point"""
    checker = QualityChecker()
    success = checker.run_all_checks()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
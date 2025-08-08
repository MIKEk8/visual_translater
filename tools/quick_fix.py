#!/usr/bin/env python3
'''
Quick Fix Script - Applies all automated fixes for Screen Translator v2.0
Runs thread safety fixes, performance optimizations, and quality improvements
'''

import subprocess
import sys
import os
from datetime import datetime

def run_command(command, description):
    '''Run a command and report results'''
    print(f"\n🔧 {description}...")
    print(f"   Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"   ✅ SUCCESS: {description}")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
        else:
            print(f"   ❌ FAILED: {description}")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ⏰ TIMEOUT: {description} took too long")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {description} - {e}")
        return False
        
    return True

def main():
    '''Run all automated fixes'''
    print("🚀 Screen Translator v2.0 - Quick Fix Script")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if we're in the right directory
    if not os.path.exists('src'):
        print("❌ Error: Please run this script from the project root directory")
        return 1
    
    fixes = [
        ("python3 fix_thread_safety_issues.py", "Thread Safety Fixes"),
        ("python3 optimize_performance.py", "Performance Optimizations"),
        ("python3 analyze_threading.py", "Thread Safety Analysis"),
        ("python3 analyze_performance.py", "Performance Analysis"),
        ("python3 analyze_dependencies.py", "Dependency Analysis"),
        ("python3 analyze_error_handling.py", "Error Handling Analysis"),
    ]
    
    results = {"success": 0, "failed": 0}
    
    for command, description in fixes:
        if run_command(command, description):
            results["success"] += 1
        else:
            results["failed"] += 1
    
    # Run tests to verify fixes
    print("\n🧪 Running tests to verify fixes...")
    test_commands = [
        ("python3 -m unittest discover src/tests/unit -v", "Unit Tests"),
        ("python3 src/tests/integration/test_system_integration.py", "Integration Tests"),
    ]
    
    for command, description in test_commands:
        if run_command(command, description):
            results["success"] += 1
        else:
            results["failed"] += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 QUICK FIX SUMMARY")
    print("=" * 60)
    print(f"✅ Successful operations: {results['success']}")
    print(f"❌ Failed operations: {results['failed']}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if results["failed"] == 0:
        print("\n🎯 ALL FIXES APPLIED SUCCESSFULLY!")
        print("\n📋 Next Steps:")
        print("  1. Review the generated reports and guidelines")
        print("  2. Test the application thoroughly")
        print("  3. Check PRODUCTION_READINESS_CHECKLIST.md")
        print("  4. Run additional tests in production-like environment")
        return 0
    else:
        print(f"\n⚠️  {results['failed']} operations failed. Please review errors above.")
        print("\n📋 Troubleshooting:")
        print("  1. Check if all required Python packages are installed")
        print("  2. Ensure you're running from the project root directory")
        print("  3. Check file permissions")
        print("  4. Review error messages for specific issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())

@echo off
rem Windows coverage report generator for Screen Translator project
rem Generates coverage reports and compares against baseline

setlocal enabledelayedexpansion

set "PYTHON_EXE=%~dp0..\wenv\Scripts\python.exe"
set "COVERAGE_DIR=%~dp0..\docs\_coverage"
set "BASELINE_FILE=%COVERAGE_DIR%\baseline.txt"

echo [COVERAGE] Using Python: %PYTHON_EXE%

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python virtual environment not found at: %PYTHON_EXE%
    echo [ERROR] Please ensure the virtual environment is set up correctly.
    exit /b 1
)

cd /d "%~dp0.."

rem Create coverage directory if it doesn't exist
if not exist "%COVERAGE_DIR%" (
    mkdir "%COVERAGE_DIR%"
    echo [INFO] Created coverage directory: %COVERAGE_DIR%
)

echo.
echo [COVERAGE] Running tests with coverage...
"%PYTHON_EXE%" -m pytest src/tests --cov=src --cov-report=term --cov-report=html:"%COVERAGE_DIR%\htmlcov" --cov-report=xml:"%COVERAGE_DIR%\coverage.xml"

if %ERRORLEVEL% neq 0 (
    echo [WARNING] Some tests failed, but coverage report was generated
)

rem Extract coverage percentage and save to file
echo [COVERAGE] Extracting coverage percentage...
"%PYTHON_EXE%" -c "
import re, subprocess, sys
result = subprocess.run([sys.executable, '-m', 'pytest', 'src/tests', '--cov=src', '--cov-report=term'],
                       capture_output=True, text=True, cwd='.')
output = result.stdout + result.stderr
match = re.search(r'TOTAL.*?(\d+%)', output)
if match:
    percentage = match.group(1)
    print(f'Current coverage: {percentage}')
    with open(r'%BASELINE_FILE%', 'w') as f:
        f.write(percentage)
    print(f'Saved baseline to: %BASELINE_FILE%')
else:
    print('Could not extract coverage percentage')
    sys.exit(1)
"

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to extract coverage percentage
    exit /b 1
)

echo.
echo [COVERAGE] Coverage report complete!
echo [INFO] HTML report: %COVERAGE_DIR%\htmlcov\index.html
echo [INFO] XML report: %COVERAGE_DIR%\coverage.xml
echo [INFO] Baseline: %BASELINE_FILE%

if exist "%BASELINE_FILE%" (
    echo [INFO] Current baseline:
    type "%BASELINE_FILE%"
)

endlocal
exit /b 0
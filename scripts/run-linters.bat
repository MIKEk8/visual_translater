@echo off
rem Windows linter runner script for Screen Translator project
rem Runs all code quality checks: flake8, mypy, black, isort

setlocal enabledelayedexpansion

set "PYTHON_EXE=%~dp0..\wenv\Scripts\python.exe"
set "FAILED=0"

echo [LINTER] Using Python: %PYTHON_EXE%

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python virtual environment not found at: %PYTHON_EXE%
    echo [ERROR] Please ensure the virtual environment is set up correctly.
    exit /b 1
)

cd /d "%~dp0.."

echo.
echo [LINTER] Running flake8...
"%PYTHON_EXE%" -m flake8 .
if %ERRORLEVEL% neq 0 (
    echo [FAILED] flake8 found issues
    set "FAILED=1"
) else (
    echo [PASSED] flake8 passed
)

echo.
echo [LINTER] Running mypy...
"%PYTHON_EXE%" -m mypy src/
if %ERRORLEVEL% neq 0 (
    echo [FAILED] mypy found issues
    set "FAILED=1"
) else (
    echo [PASSED] mypy passed
)

echo.
echo [LINTER] Running black check...
"%PYTHON_EXE%" -m black --check .
if %ERRORLEVEL% neq 0 (
    echo [FAILED] black found formatting issues
    set "FAILED=1"
) else (
    echo [PASSED] black formatting is correct
)

echo.
echo [LINTER] Running isort check...
"%PYTHON_EXE%" -m isort --check-only .
if %ERRORLEVEL% neq 0 (
    echo [FAILED] isort found import sorting issues
    set "FAILED=1"
) else (
    echo [PASSED] isort import sorting is correct
)

echo.
if "%FAILED%"=="1" (
    echo [RESULT] Some linters failed. Please fix the issues above.
    exit /b 1
) else (
    echo [RESULT] All linters passed successfully!
    exit /b 0
)

endlocal
@echo off
rem Windows test runner script for Screen Translator project
rem Usage: run-tests.bat [test-type]
rem   test-type: unit, integration, all (default: all)

setlocal enabledelayedexpansion

set "PYTHON_EXE=%~dp0..\wenv\Scripts\python.exe"
set "TEST_TYPE=%1"

if "%TEST_TYPE%"=="" set "TEST_TYPE=all"

echo [TEST-RUNNER] Using Python: %PYTHON_EXE%
echo [TEST-RUNNER] Test type: %TEST_TYPE%

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python virtual environment not found at: %PYTHON_EXE%
    echo [ERROR] Please ensure the virtual environment is set up correctly.
    exit /b 1
)

cd /d "%~dp0.."

if "%TEST_TYPE%"=="unit" (
    echo [TEST-RUNNER] Running unit tests only...
    "%PYTHON_EXE%" -m pytest src/tests/unit -v --tb=short
) else if "%TEST_TYPE%"=="integration" (
    echo [TEST-RUNNER] Running integration tests only...
    "%PYTHON_EXE%" -m pytest src/tests/integration -v --tb=short
) else if "%TEST_TYPE%"=="all" (
    echo [TEST-RUNNER] Running all tests...
    "%PYTHON_EXE%" -m pytest src/tests -v --tb=short
) else (
    echo [ERROR] Invalid test type: %TEST_TYPE%
    echo [ERROR] Valid options: unit, integration, all
    exit /b 1
)

set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% equ 0 (
    echo [TEST-RUNNER] All tests passed successfully!
) else (
    echo [TEST-RUNNER] Some tests failed. Exit code: %EXIT_CODE%
)

endlocal
exit /b %EXIT_CODE%
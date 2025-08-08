# Screen Translator v2.0 - Development Setup Complete

## Current Environment
- Platform: Linux 6.10.14-linuxkit
- Python: /usr/bin/python3
- Python Version: 3.11.2

## Usage Instructions

### Direct Python Commands:
```bash
# Install dependencies
python3 -m pip install -r requirements.txt --user
python3 -m pip install -r requirements-dev.txt --user

# Run build script
python3 build.py setup --dev
python3 build.py test
python3 build.py lint
python3 build.py build

# Run application
python3 main.py
```

### Using Build Wrapper:
```bash
# Alternative approach
python3 build_wrapper.py setup --dev
python3 build_wrapper.py test
python3 build_wrapper.py build
```

## Notes
- Dependencies installed to user site-packages
- No virtual environment needed in this setup
- All commands use system Python directly
- Compatible with current Linux container environment

## Troubleshooting
If you encounter permission errors:
- Use --user flag with pip install
- Check Python executable permissions
- Ensure workspace directory is writable

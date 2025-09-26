# 🪟 Platform Support - Windows Only

*Updated: 2025-09-26*

## 🎯 **Supported Platform**

**Screen Translator v2.0 is exclusively designed for Windows.**

### ✅ **Windows Support**
- **Windows 10** (build 1903 and later)
- **Windows 11** (all versions)
- **Windows Server 2019/2022** (limited support)

### 🛠️ **Windows-Specific Features**
- **Native Win32 API integration** for process monitoring
- **Windows hotkey management** using win32api
- **Windows-specific screen capture** with DPI awareness
- **System tray integration** using Windows notification system
- **Windows executable building** with PyInstaller

## ❌ **Unsupported Platforms**

### **Linux/macOS - Not Supported**
This application does **NOT** support Linux or macOS for the following reasons:

1. **Personal Project Scope**: Designed exclusively for developer's Windows environment
2. **Windows-Specific APIs**: Heavy reliance on Win32 APIs (win32gui, win32process, win32api)
3. **Development Focus**: All development and testing done on Windows only
4. **Maintenance**: No cross-platform testing or compatibility maintenance

## 🚨 **Important Notes**

### **For Developers**
- All code assumes Windows environment
- No cross-platform compatibility layers
- Windows-specific paths (`wenv\Scripts\` not `venv/bin/`)
- Uses Windows batch files (`.bat`) not shell scripts (`.sh`)

### **Dependencies**
Required Windows-specific packages:
- `pywin32` - Windows API bindings
- `pynput` - Windows keyboard/mouse hooks
- `pystray` - Windows system tray
- `pyinstaller` - Windows executable building

### **File Paths**
All documentation and code use Windows path conventions:
- `wenv\Scripts\python.exe` (not `venv/bin/python`)
- `config\settings.json` (not `config/settings.json`)
- `C:\Users\Username\AppData\` paths

## 🔧 **Virtual Environment**

**Windows Only**:
```cmd
# Create Windows virtual environment
python -m venv wenv

# Activate Windows virtual environment
wenv\Scripts\activate

# Install Windows dependencies
pip install -r requirements.txt
```

## 📋 **System Requirements**

### **Minimum Requirements**
- **OS**: Windows 10 build 1903+
- **Python**: 3.11 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB for application + dependencies

### **Required Software**
- **Tesseract OCR** for Windows
- **Microsoft Visual C++ Redistributable** (for some Python packages)
- **Windows Defender** exclusions may be needed for better performance

## ⚡ **Performance Optimization**

### **Windows-Specific Optimizations**
- Uses Windows performance counters
- Direct Win32 API calls for better speed
- Windows-native screenshot capture
- Optimized for Windows font rendering

### **Gaming Integration**
- DirectX/OpenGL overlay compatibility
- Windows-specific game process detection
- Steam/Epic/Origin launcher integration
- Windows Gaming Mode compatibility

## 🎮 **Gaming Platform Support**

**Supported Windows Gaming Platforms**:
- Steam (Windows client)
- Epic Games Launcher
- Origin/EA Desktop
- Uplay/Ubisoft Connect
- GOG Galaxy
- Battle.net
- Standalone Windows games

## 🚀 **Getting Started**

1. **Ensure Windows 10/11**
2. **Install Python 3.11+**
3. **Download Tesseract OCR for Windows**
4. **Run setup**: `python -m venv wenv && wenv\Scripts\activate`
5. **Install**: `pip install -r requirements.txt`
6. **Launch**: `python main.py`

## 📞 **Support**

- **Platform Issues**: Only Windows-related issues are supported
- **Cross-Platform Requests**: Will not be implemented
- **Linux/macOS Questions**: Not applicable to this project

---

**This is a Windows-only application by design.** ✅
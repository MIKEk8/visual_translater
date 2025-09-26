# 🚀 Легко реализуемые фичи для Screen Translator

*Время реализации: от 30 минут до 2 часов каждая*

## 1. 📝 **История с поиском и фильтрацией** (30 минут)

### Что есть сейчас:
- История переводов сохраняется
- Простой просмотр в HistoryWindow

### Легкое улучшение:
```python
# src/ui/history_window_enhanced.py

import sqlite3
from datetime import datetime

class EnhancedHistoryWindow:
    def __init__(self):
        self.setup_database()

    def setup_database(self):
        """Migrate to SQLite with FTS5"""
        self.conn = sqlite3.connect("translation_history.db")
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS history_fts USING fts5(
                timestamp UNINDEXED,
                source_text,
                translated_text,
                source_lang,
                target_lang,
                confidence UNINDEXED
            )
        """)

    def search_history(self, query: str):
        """Full-text search in history"""
        cursor = self.conn.execute("""
            SELECT * FROM history_fts
            WHERE history_fts MATCH ?
            ORDER BY rank
        """, (query,))
        return cursor.fetchall()

    def add_filters_to_ui(self):
        """Add search box and filters to existing UI"""
        # Search box
        self.search_var = tk.StringVar()
        search_frame = ttk.Frame(self.window)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side="left")
        ttk.Button(search_frame, text="🔍", command=self.perform_search).pack(side="left")

        # Date filter
        self.date_filter = ttk.Combobox(search_frame, values=[
            "Сегодня", "Вчера", "Последние 7 дней", "Этот месяц", "Все"
        ])
        self.date_filter.pack(side="left")
```

**Время: 30 минут** ✅

---

## 2. 🖼️ **OCR Preprocessing Pipeline** (1 час)

### Что есть:
- Прямая передача изображения в OCR
- Плохо работает с низким качеством

### Легкое улучшение:
```python
# src/core/ocr_preprocessor.py

import cv2
import numpy as np
from PIL import Image

class OCRPreprocessor:
    """Simple but effective preprocessing"""

    def preprocess(self, image: Image.Image) -> Image.Image:
        """Apply preprocessing pipeline"""
        # Convert to OpenCV format
        img_array = np.array(image)

        # 1. Grayscale conversion
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # 2. Denoise
        denoised = cv2.fastNlMeansDenoising(gray)

        # 3. Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)

        # 4. Binarization (adaptive threshold)
        binary = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # 5. Deskew (простая коррекция наклона)
        coords = np.column_stack(np.where(binary > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if angle != 0:
            (h, w) = binary.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            binary = cv2.warpAffine(binary, M, (w, h),
                                   flags=cv2.INTER_CUBIC,
                                   borderMode=cv2.BORDER_REPLICATE)

        # 6. Remove small noise
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Convert back to PIL
        return Image.fromarray(cleaned)

# Интеграция в существующий OCREngine
class EnhancedOCREngine(OCREngine):
    def __init__(self):
        super().__init__()
        self.preprocessor = OCRPreprocessor()

    def extract_text(self, image: Image.Image, preprocess: bool = True) -> str:
        if preprocess:
            image = self.preprocessor.preprocess(image)
        return super().extract_text(image)
```

**Время: 1 час** ✅

---

## 3. 📚 **Контекстные словари для игр** (45 минут)

### Легкая реализация через JSON словари:
```python
# src/core/context_glossary.py

import json
from pathlib import Path
from typing import Dict, Optional

class GameGlossary:
    """Game-specific translation glossaries"""

    def __init__(self):
        self.glossaries_path = Path("glossaries")
        self.glossaries_path.mkdir(exist_ok=True)
        self.active_glossary: Optional[Dict] = None
        self.download_popular_glossaries()

    def download_popular_glossaries(self):
        """Download from GitHub repo with game glossaries"""
        import requests

        # Примеры популярных игр
        games = {
            "genshin_impact": "https://raw.githubusercontent.com/.../genshin.json",
            "elden_ring": "https://raw.githubusercontent.com/.../elden_ring.json",
            "minecraft": "https://raw.githubusercontent.com/.../minecraft.json"
        }

        for game, url in games.items():
            glossary_file = self.glossaries_path / f"{game}.json"
            if not glossary_file.exists():
                try:
                    resp = requests.get(url)
                    glossary_file.write_text(resp.text)
                except:
                    pass

    def load_glossary(self, game_name: str):
        """Load game-specific glossary"""
        glossary_file = self.glossaries_path / f"{game_name}.json"
        if glossary_file.exists():
            self.active_glossary = json.loads(glossary_file.read_text())

    def apply_glossary(self, text: str, translation: str) -> str:
        """Replace terms according to glossary"""
        if not self.active_glossary:
            return translation

        # Simple replacement
        for term, correct_translation in self.active_glossary.items():
            # Case-insensitive replacement
            import re
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            translation = pattern.sub(correct_translation, translation)

        return translation

# Интеграция в TranslationEngine
class ContextAwareTranslator(TranslationEngine):
    def __init__(self):
        super().__init__()
        self.glossary = GameGlossary()

    def translate(self, text: str, target_lang: str, game: Optional[str] = None) -> str:
        # Базовый перевод
        translation = super().translate(text, target_lang)

        # Применяем словарь если указана игра
        if game:
            self.glossary.load_glossary(game)
            translation = self.glossary.apply_glossary(text, translation)

        return translation
```

**Время: 45 минут** ✅

---

## 4. 🎯 **Hotkey Profiles** (30 минут)

### Простые профили горячих клавиш:
```python
# src/services/hotkey_profiles.py

import json
from dataclasses import dataclass, asdict
from typing import Dict, List
from pathlib import Path

@dataclass
class HotkeyProfile:
    name: str
    description: str
    hotkeys: Dict[str, str]  # action -> key combo

class HotkeyProfileManager:
    """Manage different hotkey profiles"""

    def __init__(self):
        self.profiles_dir = Path("profiles/hotkeys")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.create_default_profiles()

    def create_default_profiles(self):
        """Create preset profiles"""
        profiles = [
            HotkeyProfile(
                "Gaming",
                "Optimized for gaming",
                {
                    "capture": "ctrl+q",  # Quick capture
                    "translate_clipboard": "ctrl+shift+t",
                    "toggle_overlay": "f1",
                    "quick_tts": "f2",
                    "pause": "f3"
                }
            ),
            HotkeyProfile(
                "Reading",
                "For reading documents",
                {
                    "capture": "ctrl+shift+c",
                    "translate_selection": "ctrl+t",
                    "lookup_word": "ctrl+l",
                    "save_to_history": "ctrl+s",
                    "export": "ctrl+e"
                }
            ),
            HotkeyProfile(
                "Streaming",
                "For watching streams",
                {
                    "capture": "f5",
                    "continuous_capture": "f6",
                    "toggle_overlay": "f7",
                    "adjust_overlay": "f8",
                    "mute_tts": "f9"
                }
            )
        ]

        for profile in profiles:
            self.save_profile(profile)

    def save_profile(self, profile: HotkeyProfile):
        """Save profile to JSON"""
        file = self.profiles_dir / f"{profile.name}.json"
        file.write_text(json.dumps(asdict(profile), indent=2))

    def load_profile(self, name: str) -> HotkeyProfile:
        """Load profile from JSON"""
        file = self.profiles_dir / f"{name}.json"
        data = json.loads(file.read_text())
        return HotkeyProfile(**data)

    def switch_profile(self, name: str):
        """Switch active hotkey profile"""
        profile = self.load_profile(name)

        # Update hotkey service
        from src.services.hotkey_service import hotkey_service
        hotkey_service.unregister_all()

        for action, keys in profile.hotkeys.items():
            hotkey_service.register(keys, action)

        # Save as active
        self.save_active_profile(name)
```

**Время: 30 минут** ✅

---

## 5. 📺 **Live Translation Mode** (2 часа)

### Базовый continuous capture:
```python
# src/core/live_translator.py

import asyncio
import time
from typing import Optional
import imagehash
from PIL import Image

class LiveTranslator:
    """Continuous screen translation"""

    def __init__(self, region=None):
        self.region = region
        self.is_running = False
        self.last_hash = None
        self.fps = 2  # Captures per second

    async def start(self):
        """Start live translation"""
        self.is_running = True

        while self.is_running:
            try:
                # Capture screen
                screenshot = self.capture_screen(self.region)

                # Check if content changed (using perceptual hash)
                current_hash = imagehash.phash(screenshot)

                if self.last_hash is None or current_hash - self.last_hash > 5:
                    # Significant change detected
                    self.last_hash = current_hash

                    # Process in background
                    asyncio.create_task(self.process_frame(screenshot))

                # Wait for next frame
                await asyncio.sleep(1.0 / self.fps)

            except Exception as e:
                logger.error(f"Live translation error: {e}")
                await asyncio.sleep(1)

    async def process_frame(self, screenshot: Image.Image):
        """Process single frame"""
        try:
            # OCR
            text = await asyncio.to_thread(ocr_engine.extract_text, screenshot)

            if text and len(text) > 10:  # Skip small text
                # Check cache first
                cached = translation_cache.get(text)
                if cached:
                    translation = cached
                else:
                    # Translate
                    translation = await asyncio.to_thread(
                        translator.translate, text, target_lang
                    )
                    translation_cache.set(text, translation)

                # Update overlay
                overlay.update_text(translation)

        except Exception as e:
            logger.error(f"Frame processing error: {e}")

    def stop(self):
        """Stop live translation"""
        self.is_running = False

# UI Integration
class LiveTranslationWindow:
    def __init__(self):
        self.setup_ui()
        self.translator = None

    def setup_ui(self):
        # Region selection
        ttk.Button(self.window, text="Выбрать область",
                  command=self.select_region).pack()

        # FPS control
        self.fps_var = tk.IntVar(value=2)
        ttk.Scale(self.window, from_=1, to=10,
                 variable=self.fps_var,
                 label="FPS").pack()

        # Start/Stop
        self.toggle_btn = ttk.Button(self.window, text="▶️ Начать",
                                    command=self.toggle_live)
        self.toggle_btn.pack()

    def toggle_live(self):
        if self.translator and self.translator.is_running:
            self.translator.stop()
            self.toggle_btn.config(text="▶️ Начать")
        else:
            self.translator = LiveTranslator(self.selected_region)
            self.translator.fps = self.fps_var.get()
            asyncio.create_task(self.translator.start())
            self.toggle_btn.config(text="⏹️ Остановить")
```

**Время: 2 часа** ✅

---

## 6. 🎮 **Auto Game Detection** (1 час)

### Автоопределение активной игры:
```python
# src/core/game_detector.py

import psutil
import win32gui
import win32process
from typing import Optional

class GameDetector:
    """Detect running game automatically"""

    # Known games database
    GAME_DATABASE = {
        "GenshinImpact.exe": "genshin_impact",
        "eldenring.exe": "elden_ring",
        "Minecraft.exe": "minecraft",
        "witcher3.exe": "witcher3",
        "FFXIV_DX11.exe": "ffxiv",
        # ... добавить больше игр
    }

    def __init__(self):
        self.current_game = None
        self.check_interval = 5  # seconds

    def get_active_window_process(self) -> Optional[str]:
        """Get process name of active window"""
        try:
            # Get active window
            hwnd = win32gui.GetForegroundWindow()

            # Get process ID
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            # Get process name
            process = psutil.Process(pid)
            return process.name()

        except Exception as e:
            logger.error(f"Failed to get active process: {e}")
            return None

    def detect_game(self) -> Optional[str]:
        """Detect if known game is running"""
        process_name = self.get_active_window_process()

        if process_name in self.GAME_DATABASE:
            game_id = self.GAME_DATABASE[process_name]

            if game_id != self.current_game:
                self.current_game = game_id
                self.on_game_changed(game_id)

            return game_id

        return None

    def on_game_changed(self, game_id: str):
        """Handle game change event"""
        logger.info(f"Game detected: {game_id}")

        # Load game-specific settings
        self.load_game_config(game_id)

        # Load game glossary
        glossary_manager.load_glossary(game_id)

        # Switch hotkey profile
        hotkey_profiles.switch_profile(f"game_{game_id}")

        # Show notification
        tray_icon.notify(f"Игра определена: {game_id}",
                        "Настройки загружены")

    def load_game_config(self, game_id: str):
        """Load game-specific configuration"""
        config_file = Path(f"configs/games/{game_id}.json")

        if config_file.exists():
            config = json.loads(config_file.read_text())

            # Apply OCR settings
            if "ocr" in config:
                ocr_engine.set_language(config["ocr"]["language"])
                ocr_engine.set_preprocessing(config["ocr"]["preprocess"])

            # Apply overlay settings
            if "overlay" in config:
                overlay.set_position(config["overlay"]["position"])
                overlay.set_style(config["overlay"]["style"])

# Background monitoring
async def monitor_games():
    detector = GameDetector()

    while True:
        detector.detect_game()
        await asyncio.sleep(detector.check_interval)
```

**Время: 1 час** ✅

---

## 7. 📋 **Quick Actions Menu** (30 минут)

### Быстрое контекстное меню:
```python
# src/ui/quick_actions.py

import tkinter as tk
from tkinter import ttk

class QuickActionsMenu:
    """Floating quick actions menu"""

    def __init__(self):
        self.create_menu()

    def create_menu(self):
        """Create floating menu window"""
        self.menu = tk.Toplevel()
        self.menu.overrideredirect(True)  # No title bar
        self.menu.attributes("-topmost", True)
        self.menu.attributes("-alpha", 0.9)

        # Compact button grid
        actions = [
            ("📷", self.quick_capture, "Захват"),
            ("🔄", self.retry_last, "Повторить"),
            ("📝", self.edit_last, "Изменить"),
            ("🔊", self.speak_last, "Озвучить"),
            ("💾", self.save_last, "Сохранить"),
            ("📊", self.show_stats, "Статистика"),
        ]

        for i, (icon, command, tooltip) in enumerate(actions):
            btn = ttk.Button(self.menu, text=icon, command=command, width=3)
            btn.grid(row=0, column=i, padx=1, pady=1)

            # Tooltip
            self.create_tooltip(btn, tooltip)

    def show_at_cursor(self):
        """Show menu at cursor position"""
        x, y = self.menu.winfo_pointerxy()
        self.menu.geometry(f"+{x}+{y}")
        self.menu.deiconify()

        # Auto-hide after 5 seconds
        self.menu.after(5000, self.menu.withdraw)

    def quick_capture(self):
        """Quick capture with last settings"""
        if hasattr(self, 'last_region'):
            screenshot = capture_screen(self.last_region)
            process_screenshot(screenshot)
```

**Время: 30 минут** ✅

---

## 8. 🔗 **URL/File Drop Support** (45 минут)

### Drag & Drop для файлов и URL:
```python
# src/ui/drop_zone.py

import tkinterdnd2 as tkdnd
from urllib.parse import urlparse
import requests
from PIL import Image
from io import BytesIO

class DropZone:
    """Universal drop zone for files and URLs"""

    def __init__(self, parent):
        self.create_drop_zone(parent)

    def create_drop_zone(self, parent):
        """Create drop zone widget"""
        self.drop_frame = ttk.LabelFrame(parent, text="Перетащите сюда")
        self.drop_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Drop label
        self.drop_label = ttk.Label(
            self.drop_frame,
            text="📥\nПеретащите изображения, PDF или URL",
            font=("Arial", 12)
        )
        self.drop_label.pack(pady=50)

        # Enable drag and drop
        self.drop_frame.drop_target_register(tkdnd.DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)

    def on_drop(self, event):
        """Handle dropped items"""
        files = self.parse_drop_data(event.data)

        for file_path in files:
            if self.is_url(file_path):
                self.process_url(file_path)
            else:
                self.process_file(file_path)

    def is_url(self, text: str) -> bool:
        """Check if text is URL"""
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except:
            return False

    def process_url(self, url: str):
        """Process dropped URL"""
        try:
            # Download image from URL
            response = requests.get(url, timeout=10)
            img = Image.open(BytesIO(response.content))

            # Process as screenshot
            text = ocr_engine.extract_text(img)
            translation = translator.translate(text, target_lang)

            # Show result
            self.show_result(translation, source_url=url)

        except Exception as e:
            logger.error(f"Failed to process URL: {e}")

    def process_file(self, file_path: str):
        """Process dropped file"""
        path = Path(file_path)

        if path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp']:
            # Image file
            img = Image.open(path)
            text = ocr_engine.extract_text(img)
            translation = translator.translate(text, target_lang)
            self.show_result(translation, source_file=path)

        elif path.suffix.lower() == '.pdf':
            # PDF file (если добавить поддержку)
            self.process_pdf(path)
```

**Время: 45 минут** ✅

---

## 📊 Сводная таблица реализации

| Фича | Сложность | Время | Приоритет | ROI |
|------|-----------|-------|-----------|-----|
| **История с поиском** | ⭐ | 30 мин | Высокий | 10/10 |
| **Hotkey Profiles** | ⭐ | 30 мин | Высокий | 9/10 |
| **Game Detection** | ⭐⭐ | 1 час | Высокий | 9/10 |
| **OCR Preprocessing** | ⭐⭐ | 1 час | Высокий | 8/10 |
| **Quick Actions** | ⭐ | 30 мин | Средний | 8/10 |
| **Контекстные словари** | ⭐⭐ | 45 мин | Средний | 7/10 |
| **Drop Zone** | ⭐⭐ | 45 мин | Средний | 7/10 |
| **Live Translation** | ⭐⭐⭐ | 2 часа | Низкий | 6/10 |

## 🎯 Рекомендуемый порядок реализации

### День 1 (2 часа):
1. ✅ История с поиском (30 мин)
2. ✅ Hotkey Profiles (30 мин)
3. ✅ Quick Actions Menu (30 мин)
4. ✅ Game Detection (основа) (30 мин)

### День 2 (2 часа):
5. ✅ OCR Preprocessing (1 час)
6. ✅ Контекстные словари (45 мин)
7. ✅ Тестирование (15 мин)

### День 3 (2 часа):
8. ✅ Drop Zone (45 мин)
9. ✅ Live Translation (1 час 15 мин)

**Итого: 6 часов чистого времени = 3 вечера по 2 часа**

Все фичи используют существующую архитектуру и не требуют рефакторинга!
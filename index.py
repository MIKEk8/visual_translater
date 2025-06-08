import json
import tkinter as tk
from tkinter import messagebox
import keyboard
import pytesseract
from PIL import ImageGrab, ImageEnhance, Image
from googletrans import Translator
import pyttsx3
import pystray
import ctypes
import sys
import os
import queue
import threading
from datetime import datetime

# Конфигурация
ICON_PATH = "icon.ico"
HOTKEY = 'alt+a'
DEBUG_MODE = False
MIN_AREA_SIZE = 50  # Минимальный размер области в пикселях

class TrayApp:
    def __init__(self):
        self.gui_queue = queue.Queue()
        self.translator = ScreenTranslator(self)
        self.icon = None
        self.setup_tray()
        self.check_messages()

    def setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem('Сделать скриншот', self.activate_capture, default=True),
            pystray.MenuItem('Лог', self.show_log),
            pystray.MenuItem('Выход', self.exit_app)
        )
        self.icon = pystray.Icon(
            "screen_translator",
            self.load_icon(),
            menu=menu
        )
        self.icon.run_detached()

    def show_log(self):
        with open('log.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(self.translator.logs, indent=2, ensure_ascii=False))
        os.startfile('log.json')

    def load_icon(self):
        try:
            return Image.open(ICON_PATH)
        except:
            return Image.new('RGB', (64, 64), 'white')

    def check_messages(self):
        try:
            while not self.gui_queue.empty():
                func, args = self.gui_queue.get_nowait()
                func(*args)
        except Exception as e:
            print(f"Ошибка в очереди: {str(e)}")
        self.translator.root.after(100, self.check_messages)

    def activate_capture(self):
        self.translator.root.after(0, self.translator.capture_area)

    def exit_app(self):
        self.translator.root.after(0, self.translator.shutdown)
        self.icon.visible = False
        self.icon.stop()

class ScreenTranslator:
    def __init__(self, tray_app):
        self.tray_app = tray_app
        self.root = tk.Tk()
        self.root.withdraw()
        self.setup_ocr()
        self.engine = pyttsx3.init()
        self.translator = Translator()
        self.engine_initialized = True
        self.setup_hotkey()
        self.check_dependencies()
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.setup_gui()
        self.logs = []

    def setup_gui(self):
        self.root.attributes('-alpha', 0.3)
        self.root.configure(background='black')
        self.root.attributes('-fullscreen', True)
        self.root.overrideredirect(True)
        self.canvas = tk.Canvas(self.root, cursor='cross', bg='grey11')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.root.withdraw()

    def on_close(self):
        self.root.withdraw()

    def setup_ocr(self):
        try:
            paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
            ]
            for path in paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    return
            raise Exception("Tesseract не найден!")
        except Exception as e:
            self.show_error(f"Ошибка Tesseract: {str(e)}")

    def setup_hotkey(self):
        keyboard.add_hotkey(HOTKEY, self.capture_area)

    def check_dependencies(self):
        if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
            self.show_error("Tesseract OCR не установлен!", exit=True)

    def capture_area(self):
        self.root.deiconify()
        self.root.attributes('-topmost', True)
        self.root.focus_force()
        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)

    def on_press(self, event):
        self.start_x = event.x_root  # Используем абсолютные координаты экрана
        self.start_y = event.y_root
        if DEBUG_MODE:
            print(f"Начальные координаты: X={self.start_x}, Y={self.start_y}")
        
        # Координаты на канвасе
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(
            canvas_x, canvas_y, canvas_x, canvas_y, outline='red')

    def on_drag(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, canvas_x, canvas_y)

    def on_release(self, event):
        self.canvas.delete(self.rect)
        self.root.withdraw()  # Сразу скрываем окно при отпускании
        
        # Получаем абсолютные координаты с учетом DPI
        x1 = min(self.start_x, event.x_root)
        y1 = min(self.start_y, event.y_root)
        x2 = max(self.start_x, event.x_root)
        y2 = max(self.start_y, event.y_root)


        threading.Thread(target=self.process_screenshot, args=(x1, y1, x2, y2), daemon=True).start()


    def process_screenshot(self, x1, y1, x2, y2):
        try:
            # Захват области с учетом границ экрана
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            x1 = max(0, min(x1, screen_width))
            x2 = max(0, min(x2, screen_width))
            y1 = max(0, min(y1, screen_height))
            y2 = max(0, min(y2, screen_height))

            DPI_SCALE = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
            x1 = int(x1 * DPI_SCALE)
            x2 = int(x2 * DPI_SCALE)
            y1 = int(y1 * DPI_SCALE)
            y2 = int(y2 * DPI_SCALE)
            
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            
            # Отладочное сохранение
            if DEBUG_MODE:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                screenshot.save(filename)
                print(f"Скриншот сохранен: {filename}")

            # Улучшение изображения
            enhancer = ImageEnhance.Contrast(screenshot)
            screenshot = enhancer.enhance(1.5)
            
            # Распознавание текста
            text = pytesseract.image_to_string(screenshot, lang='eng+rus').strip()
            text = self.replace_special_chars(text)
            if not text:
                return
                
            if DEBUG_MODE:
                print(f"Распознанный текст ({len(text)} символов):\n{text}")

            # Перевод
            try:
                self.logs.append(text)
                translated = self.translator.translate(text, dest='ru').text
                self.logs.append(translated)
            except Exception as e:
                self.show_error(f"Ошибка перевода: {str(e)}")
                return
                
            if DEBUG_MODE:
                print(f"Перевод ({len(translated)} символов):\n{translated}")

            # Озвучка
            if self.engine_initialized:
                self.engine.say(translated)
                self.engine.runAndWait()
            
        except Exception as e:
            self.show_error(f"Ошибка обработки: {str(e)}")
        finally:
            if self.engine_initialized:
                self.engine.stop()
            self.root.after(0, self.root.withdraw)  # Двойное подтверждение закрытия
            
    def replace_special_chars(self, text):
        replacements = {
            '1': 'I',
            '0': 'O',
            '\n': ' ',
            '\r': ' ',
            '\t': ' ',
            '_': ' ',
        }
        
        # Производим замену символов
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        # Удаляем лишние пробелы
        return ' '.join(text.split())

    def show_warning(self, message):
        self.root.after(0, lambda: messagebox.showwarning("Предупреждение", message))

    def shutdown(self):
        self.engine_initialized = False
        self.root.destroy()
        os._exit(0)

    def show_error(self, message, exit=False):
        self.root.after(0, lambda: messagebox.showerror("Ошибка", message))
        if exit:
            self.shutdown()

if __name__ == "__main__":
    if sys.platform != 'win32':
        print("Приложение работает только на Windows")
        sys.exit(1)
        
    if not os.path.exists(ICON_PATH):
        print(f"Предупреждение: Иконка {ICON_PATH} не найдена!")
        
    if sys.executable.endswith("pythonw.exe"):
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    
    app = TrayApp()
    app.translator.root.mainloop()
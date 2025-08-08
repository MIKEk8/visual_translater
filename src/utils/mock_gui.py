"""
Enhanced Mock GUI модули для тестирования в среде без GUI
Предоставляет заглушки для всех основных tkinter компонентов
"""


class MockEvent:
    """Mock для tkinter Event"""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        # Стандартные атрибуты события
        self.delta = getattr(self, "delta", 0)
        self.x = getattr(self, "x", 0)
        self.y = getattr(self, "y", 0)
        self.x_root = getattr(self, "x_root", 0)
        self.y_root = getattr(self, "y_root", 0)


class MockWidget:
    """Базовый mock для tkinter Widget"""

    def __init__(self, parent=None, **kwargs):
        self.parent = parent
        self.children = []
        self._config = kwargs
        self.winfo_x_value = 0
        self.winfo_y_value = 0
        self.winfo_width_value = 100
        self.winfo_height_value = 50

        # Стандартные атрибуты
        for key, value in kwargs.items():
            setattr(self, key, value)

    def pack(self, **kwargs):
        return self

    def grid(self, **kwargs):
        return self

    def place(self, **kwargs):
        return self

    def configure(self, **kwargs):
        self._config.update(kwargs)
        return self

    def config(self, **kwargs):
        return self.configure(**kwargs)

    def bind(self, event, callback):
        return self

    def unbind(self, event):
        return self

    def winfo_x(self):
        return self.winfo_x_value

    def winfo_y(self):
        return self.winfo_y_value

    def winfo_width(self):
        return self.winfo_width_value

    def winfo_height(self):
        return self.winfo_height_value

    def winfo_rootx(self):
        return self.winfo_x_value

    def winfo_rooty(self):
        return self.winfo_y_value

    def winfo_exists(self):
        return True

    def destroy(self):
        if self.parent and hasattr(self.parent, "children"):
            try:
                self.parent.children.remove(self)
            except ValueError:
                pass


class MockTk(MockWidget):
    """Mock для tkinter.Tk"""

    def __init__(self):
        super().__init__()
        self.title_text = "Mock Window"

    def title(self, text=None):
        if text is not None:
            self.title_text = text
        return self.title_text

    def geometry(self, geometry=None):
        return self

    def resizable(self, width=True, height=True):
        return self

    def mainloop(self):
        print("Mock mainloop завершен")

    def quit(self):
        print("Mock quit вызван")

    def withdraw(self):
        print("Mock withdraw вызван")

    def deiconify(self):
        print("Mock deiconify вызван")

    def iconify(self):
        print("Mock iconify вызван")

    def attributes(self, *args, **kwargs):
        return self

    def protocol(self, protocol, callback):
        return self

    def after(self, delay, callback=None, *args):
        if callback:
            try:
                callback(*args)
            except:
                pass
        return self


class MockToplevel(MockWidget):
    """Mock для tkinter.Toplevel"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title_text = "Mock Toplevel"

    def title(self, text=None):
        if text is not None:
            self.title_text = text
        return self.title_text

    def geometry(self, geometry=None):
        return self

    def transient(self, parent):
        return self

    def grab_set(self):
        return self

    def grab_release(self):
        return self


class MockFrame(MockWidget):
    """Mock для tkinter.Frame"""

    pass


class MockLabel(MockWidget):
    """Mock для tkinter.Label"""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.text_value = kwargs.get("text", "")

    def configure(self, **kwargs):
        if "text" in kwargs:
            self.text_value = kwargs["text"]
        return super().configure(**kwargs)


class MockButton(MockWidget):
    """Mock для tkinter.Button"""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.command = kwargs.get("command", lambda: None)
        self.text_value = kwargs.get("text", "Button")

    def invoke(self):
        if self.command:
            try:
                self.command()
            except:
                pass


class MockEntry(MockWidget):
    """Mock для tkinter.Entry"""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.value = kwargs.get("value", "")

    def get(self):
        return self.value

    def set(self, value):
        self.value = str(value)

    def insert(self, index, value):
        self.value = str(value)

    def delete(self, start, end=None):
        self.value = ""


class MockText(MockWidget):
    """Mock для tkinter.Text"""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.content = ""

    def get(self, start, end=None):
        return self.content

    def insert(self, index, text):
        self.content += str(text)

    def delete(self, start, end=None):
        self.content = ""

    def see(self, index):
        return self


class MockCanvas(MockWidget):
    """Mock для tkinter.Canvas"""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

    def create_rectangle(self, *args, **kwargs):
        return 1

    def create_text(self, *args, **kwargs):
        return 2

    def delete(self, *args):
        return self

    def yview_scroll(self, number, what):
        return self

    def configure(self, **kwargs):
        if "scrollregion" in kwargs:
            pass  # Обрабатываем scrollregion
        return super().configure(**kwargs)


class MockScrollbar(MockWidget):
    """Mock для tkinter.Scrollbar"""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

    def set(self, first, last):
        return self


class MockCombobox(MockWidget):
    """Mock для ttk.Combobox"""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.values_list = kwargs.get("values", [])
        self.current_value = ""

    def get(self):
        return self.current_value

    def set(self, value):
        self.current_value = str(value)

    def configure(self, **kwargs):
        if "values" in kwargs:
            self.values_list = kwargs["values"]
        return super().configure(**kwargs)


class MockStringVar:
    """Mock для tkinter.StringVar"""

    def __init__(self, value=""):
        self.value = str(value)

    def get(self):
        return self.value

    def set(self, value):
        self.value = str(value)


class MockIntVar:
    """Mock для tkinter.IntVar"""

    def __init__(self, value=0):
        self.value = int(value)

    def get(self):
        return self.value

    def set(self, value):
        self.value = int(value)


class MockTkinter:
    """Главный mock для tkinter модуля"""

    # Widget classes
    Widget = MockWidget  # Базовый класс Widget
    Event = MockEvent  # Event класс
    Tk = MockTk
    Toplevel = MockToplevel
    Frame = MockFrame
    Label = MockLabel
    Button = MockButton
    Entry = MockEntry
    Text = MockText
    Canvas = MockCanvas
    Scrollbar = MockScrollbar

    # Variables
    StringVar = MockStringVar
    IntVar = MockIntVar

    # Constants
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    BOTH = "both"
    X = "x"
    Y = "y"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"
    END = "end"
    INSERT = "insert"
    DISABLED = "disabled"
    NORMAL = "normal"
    ACTIVE = "active"

    # Geometry managers constants
    PACK = "pack"
    GRID = "grid"
    PLACE = "place"

    # Event constants
    Button1 = "<Button-1>"
    Button3 = "<Button-3>"
    KeyPress = "<KeyPress>"
    KeyRelease = "<KeyRelease>"
    Motion = "<Motion>"
    Enter = "<Enter>"
    Leave = "<Leave>"


class MockTTK:
    """Mock для tkinter.ttk модуля"""

    Combobox = MockCombobox
    Frame = MockFrame
    Label = MockLabel
    Button = MockButton


# Экспорт основных компонентов
tk = MockTkinter()
ttk = MockTTK()

# Экспорт отдельных компонентов для from imports
Widget = MockWidget
Event = MockEvent
Tk = MockTk
Toplevel = MockToplevel
Frame = MockFrame
Label = MockLabel
Button = MockButton
Entry = MockEntry
Text = MockText
Canvas = MockCanvas
Scrollbar = MockScrollbar
StringVar = MockStringVar
IntVar = MockIntVar

# Constants для from imports
HORIZONTAL = "horizontal"
VERTICAL = "vertical"
BOTH = "both"
X = "x"
Y = "y"
LEFT = "left"
RIGHT = "right"
TOP = "top"
BOTTOM = "bottom"
CENTER = "center"
END = "end"
INSERT = "insert"
DISABLED = "disabled"
NORMAL = "normal"
ACTIVE = "active"


def messagebox():
    """Mock для tkinter.messagebox"""

    class MockMessageBox:
        @staticmethod
        def showinfo(title, message):
            print(f"INFO: {title}: {message}")

        @staticmethod
        def showwarning(title, message):
            print(f"WARNING: {title}: {message}")

        @staticmethod
        def showerror(title, message):
            print(f"ERROR: {title}: {message}")

        @staticmethod
        def askquestion(title, message):
            print(f"QUESTION: {title}: {message}")
            return "yes"

        @staticmethod
        def askyesno(title, message):
            print(f"YES/NO: {title}: {message}")
            return True

    return MockMessageBox()


def filedialog():
    """Mock для tkinter.filedialog"""

    class MockFileDialog:
        @staticmethod
        def askopenfilename(**kwargs):
            return "/mock/path/file.txt"

        @staticmethod
        def asksaveasfilename(**kwargs):
            return "/mock/path/save.txt"

        @staticmethod
        def askdirectory(**kwargs):
            return "/mock/path/directory"

    return MockFileDialog()


print("Mock GUI модули загружены успешно")

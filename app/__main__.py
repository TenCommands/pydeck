import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QUrl
from bs4 import BeautifulSoup

# Directory containing 0.html, 1.html, 2.html, etc.
SLIDES_DIR = Path("presentation")
current_index = 0


def get_slide_files():
    files = sorted(
        [f for f in SLIDES_DIR.glob("*.html") if f.stem.isdigit()],
        key=lambda x: int(x.stem)
    )
    return files


def extract_mode_html(file_path, mode):
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    if mode == "presentation":
        notes = soup.find(id="notes")
        if notes:
            notes.decompose()
    elif mode == "notes":
        presentation = soup.find(id="presentation")
        if presentation:
            presentation.decompose()

    return str(soup)


class SlideWindow(QWidget):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self.setWindowTitle(mode.capitalize())

        self.browser = QWebEngineView()
        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        self.setLayout(layout)

    def load_slide(self, file_path):
        html = extract_mode_html(file_path, self.mode)
        self.browser.setHtml(html, QUrl.fromLocalFile(str(file_path.resolve())))


class PresentationController:
    def __init__(self):
        self.slides = get_slide_files()
        if not self.slides:
            raise Exception("No slides found (0.html, 1.html, etc.)")

        self.presentation_window = SlideWindow("presentation")
        self.notes_window = SlideWindow("notes")

        self.presentation_window.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.presentation_window.move(0,0)
        self.presentation_window.showFullScreen()
        self.notes_window.move(1920, 100)
        self.notes_window.showFullScreen()

        self.load_slide(0)

        self.presentation_window.show()
        self.notes_window.show()

        # Capture key events globally
        self.presentation_window.keyPressEvent = self.keyPressEvent # type: ignore
        self.notes_window.keyPressEvent = self.keyPressEvent # type: ignore

    def load_slide(self, index):
        global current_index
        current_index = index

        file_path = self.slides[current_index]

        self.presentation_window.load_slide(file_path)
        self.notes_window.load_slide(file_path)

        self.presentation_window.setWindowTitle(f"Presentation - Slide {current_index}")
        self.notes_window.setWindowTitle(f"Notes - Slide {current_index}")

    def keyPressEvent(self, event):
        global current_index

        if event.key() == Qt.Key.Key_Right:
            if current_index < len(self.slides) - 1:
                self.load_slide(current_index + 1)

        elif event.key() == Qt.Key.Key_Left:
            if current_index > 0:
                self.load_slide(current_index - 1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = PresentationController()
    sys.exit(app.exec())

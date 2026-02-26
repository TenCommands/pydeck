import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QUrl, QFileSystemWatcher, QTimer
from bs4 import BeautifulSoup

SLIDES_DIR = Path("presentation")
current_index = 0


def get_slide_files():
    return sorted(
        [f for f in SLIDES_DIR.glob("*.html") if f.stem.isdigit()],
        key=lambda x: int(x.stem)
    )


def get_css_files():
    return list(SLIDES_DIR.rglob("*.css"))


def extract_mode_html(file_path, mode):
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    container = soup.find(id=mode)
    if not container:
        return str(soup)

    # Remove the other container
    if mode == "presentation":
        other = soup.find(id="notes")
    else:
        other = soup.find(id="presentation")
    if other:
        other.decompose()

    # Inject transition CSS + JS
    injection = """
<style>
.slide-enter { animation: slideEnter 0.5s ease forwards; }
.slide-exit { animation: slideExit 0.4s ease forwards; }

@keyframes slideEnter {
  from { opacity: 0; transform: translateX(30px); }
  to   { opacity: 1; transform: translateX(0); }
}

@keyframes slideExit {
  from { opacity: 1; transform: translateX(0); }
  to   { opacity: 0; transform: translateX(-30px); }
}
</style>

<script>
let presentationStart = Date.now();

function updateTimer() {
    document.querySelectorAll("[data-timer]").forEach(el => {
        let elapsed = Math.floor((Date.now() - presentationStart) / 1000);
        let mins = Math.floor(elapsed / 60);
        let secs = elapsed % 60;
        el.innerText = mins.toString().padStart(2,"0") + ":" +
                       secs.toString().padStart(2,"0");
    });
}

function updateClock() {
    document.querySelectorAll("[data-clock]").forEach(el => {
        let now = new Date();
        el.innerText = now.toLocaleTimeString();
    });
}

setInterval(updateTimer, 500);
setInterval(updateClock, 1000);
</script>
"""

    if soup.head:
        soup.head.append(BeautifulSoup(injection, "html.parser"))

    return str(soup)


class SlideWindow(QWidget):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
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

        self.setup_monitors()

        self.presentation_window.keyPressEvent = self.keyPressEvent  # type: ignore
        self.notes_window.keyPressEvent = self.keyPressEvent  # type: ignore

        # ---- FILE WATCHER ----
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self.on_directory_changed)
        self.watcher.fileChanged.connect(self.on_file_changed)

        self.watch_all_files()

        self.load_slide(0)

        self.presentation_window.show()
        self.notes_window.show()

    # -------------------------
    # MONITOR DETECTION
    # -------------------------
    def setup_monitors(self):
        screens = QApplication.screens()

        if len(screens) > 1:
            primary = screens[0]
            secondary = screens[1]

            # Presentation on secondary (projector)
            self.presentation_window.setGeometry(secondary.geometry())
            self.presentation_window.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.presentation_window.showFullScreen()

            # Notes on primary
            self.notes_window.setGeometry(primary.geometry())
            self.notes_window.showFullScreen()
        else:
            # Fallback single monitor
            screen = screens[0]
            self.presentation_window.setGeometry(screen.geometry())
            self.presentation_window.showFullScreen()

            self.notes_window.resize(800, 600)
            self.notes_window.move(100, 100)

    # -------------------------
    # FILE WATCHING
    # -------------------------
    def watch_all_files(self):
        self.watcher.removePaths(self.watcher.files())
        self.watcher.removePaths(self.watcher.directories())

        # Watch folder
        self.watcher.addPath(str(SLIDES_DIR))

        # Watch all html
        for slide in self.slides:
            self.watcher.addPath(str(slide))

        # Watch all css
        for css in get_css_files():
            self.watcher.addPath(str(css))

    def on_directory_changed(self, path):
        self.slides = get_slide_files()
        self.watch_all_files()

    def on_file_changed(self, path):
        QTimer.singleShot(100, self.reload_current_slide)

    def reload_current_slide(self):
        self.load_slide(current_index)

    # -------------------------
    # SLIDE CONTROL
    # -------------------------
    def load_slide(self, index):
        global current_index

        old_index = current_index
        current_index = index

        self.slides = get_slide_files()
        file_path = self.slides[current_index]

        # Play exit animation first
        for window in [self.presentation_window, self.notes_window]:
            window.browser.page().runJavaScript( # type: ignore
                """
                let container = document.body.firstElementChild;
                if (container) container.classList.add("slide-exit");
            """) 

        QTimer.singleShot(400, lambda: self.finish_slide_load(file_path))


    def finish_slide_load(self, file_path):
        self.presentation_window.load_slide(file_path)
        self.notes_window.load_slide(file_path)

        QTimer.singleShot(50, lambda: self.play_enter_animation())


    def play_enter_animation(self):
        for window in [self.presentation_window, self.notes_window]:
            window.browser.page().runJavaScript( # type: ignore
                """
                let container = document.body.firstElementChild;
                if (container) container.classList.add("slide-enter");
            """)

    def keyPressEvent(self, event):
        global current_index

        if event.key() == Qt.Key.Key_Right:
            if current_index < len(self.slides) - 1:
                self.load_slide(current_index + 1)

        elif event.key() == Qt.Key.Key_Left:
            if current_index > 0:
                self.load_slide(current_index - 1)

        elif event.key() == Qt.Key.Key_Escape:
            QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = PresentationController()
    sys.exit(app.exec())
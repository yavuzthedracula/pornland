import os
import re
import json
import requests
from bs4 import BeautifulSoup
from PyQt5 import QtWidgets, QtCore, QtGui
import sys

class DownloadItem(QtWidgets.QWidget):
    def __init__(self, page_url, headers, cookies, parent=None):
        super().__init__(parent)
        self.page_url = page_url
        self.headers = headers
        self.cookies = cookies
        self.video_title = "video"
        self.last_media_url = ""
        self.cover_image_url = ""
        self.video_data = []
        self.quality_options = []
        self.selected_quality_url = None
        self.init_ui()
        self.start_find()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Cover Image Label
        self.cover_image_label = QtWidgets.QLabel(self)
        self.cover_image_label.setFixedHeight(120)  # Adjust height as needed
        self.cover_image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.cover_image_label.setStyleSheet("background-color: #1E1E1E; border-radius: 5px;")
        main_layout.addWidget(self.cover_image_label)

        # Title Label
        self.title_label = QtWidgets.QLabel("Finding video title...", self)
        font = QtGui.QFont("Poppins SemiBold", 10)
        self.title_label.setFont(font)
        main_layout.addWidget(self.title_label)

        # Control Layout
        control_layout = QtWidgets.QHBoxLayout()
        control_layout.setSpacing(10)

        self.quality_combo = QtWidgets.QComboBox(self)
        self.quality_combo.setEnabled(False)
        self.quality_combo.setMinimumWidth(100)
        control_layout.addWidget(self.quality_combo)

        self.download_button = QtWidgets.QPushButton("Download", self)
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.download_video)
        control_layout.addWidget(self.download_button)

        main_layout.addLayout(control_layout)

        # Status Label
        self.status_label = QtWidgets.QLabel("Status: Initializing...", self)
        self.status_label.setFont(QtGui.QFont("Poppins Medium", 9))
        main_layout.addWidget(self.status_label)

        # Progress Layout
        progress_layout = QtWidgets.QHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(5)

        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #FFA500;
                border-radius: 5px;
                background-color: #333333;
            }
            QProgressBar::chunk {
                background-color: #FFA500;
                width: 20px;
            }
        """)
        self.progress_bar.setFixedHeight(20)
        progress_layout.addWidget(self.progress_bar, stretch=1)

        self.progress_label = QtWidgets.QLabel("0%", self)
        self.progress_label.setAlignment(QtCore.Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #FFA500;")
        self.progress_label.setFont(QtGui.QFont("Poppins Medium", 9))
        self.progress_label.setFixedWidth(50)
        progress_layout.addWidget(self.progress_label)

        progress_layout.addStretch()

        main_layout.addLayout(progress_layout)

        self.setLayout(main_layout)
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                border: 1px solid #444444;
                border-radius: 5px;
            }
            QLabel {
                color: #FFFFFF;
                font-family: "Poppins";
                font-weight: 500;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #FFA500;
                border-radius: 3px;
                background-color: #1E1E1E;
                color: #FFFFFF;
                font-family: "Poppins";
                font-weight: 500;
            }
            QPushButton {
                background-color: #FFA500;
                color: #1B1B1B;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-family: "Poppins";
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e69500;
            }
            QPushButton:disabled {
                background-color: #666666;
            }
        """)
        self.setFixedHeight(250)  # Adjust height to accommodate image

    def start_find(self):
        self.find_thread = QtCore.QThread()
        self.find_worker = FindWorker(self.page_url, self.headers, self.cookies)
        self.find_worker.moveToThread(self.find_thread)

        self.find_thread.started.connect(self.find_worker.run)
        self.find_worker.finished.connect(self.on_find_finished)
        self.find_worker.error.connect(self.on_error)

        self.find_worker.finished.connect(self.find_thread.quit)
        self.find_worker.finished.connect(self.find_worker.deleteLater)
        self.find_thread.finished.connect(self.find_thread.deleteLater)

        self.find_thread.start()

    def on_find_finished(self, media_definitions, video_title, last_media_url, cover_image_url):
        self.video_title = video_title
        self.last_media_url = last_media_url
        self.cover_image_url = cover_image_url
        self.title_label.setText(f"Title: {self.video_title}")

        if self.cover_image_url:
            self.fetch_cover_image(self.cover_image_url)
        else:
            self.cover_image_label.setText("No Cover Image Found")

        if not self.last_media_url:
            self.status_label.setText("Status: Last media URL not found.")
            return

        self.status_label.setText("Status: Fetching video data...")

        self.video_data_thread = QtCore.QThread()
        self.video_data_worker = VideoDataWorker(self.last_media_url, self.headers, self.cookies)
        self.video_data_worker.moveToThread(self.video_data_thread)

        self.video_data_thread.started.connect(self.video_data_worker.run)
        self.video_data_worker.finished.connect(self.on_video_data_fetched)
        self.video_data_worker.error.connect(self.on_error)

        self.video_data_worker.finished.connect(self.video_data_thread.quit)
        self.video_data_worker.finished.connect(self.video_data_worker.deleteLater)
        self.video_data_thread.finished.connect(self.video_data_thread.deleteLater)

        self.video_data_thread.start()

    def fetch_cover_image(self, image_url):
        self.image_fetch_thread = QtCore.QThread()
        self.image_fetch_worker = ImageFetchWorker(image_url)
        self.image_fetch_worker.moveToThread(self.image_fetch_thread)

        self.image_fetch_thread.started.connect(self.image_fetch_worker.run)
        self.image_fetch_worker.finished.connect(self.on_image_fetched)
        self.image_fetch_worker.error.connect(self.on_error)

        self.image_fetch_worker.finished.connect(self.image_fetch_thread.quit)
        self.image_fetch_worker.finished.connect(self.image_fetch_worker.deleteLater)
        self.image_fetch_thread.finished.connect(self.image_fetch_thread.deleteLater)

        self.image_fetch_thread.start()

    def on_image_fetched(self, image_data):
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(image_data)
        if not pixmap.isNull():
            # Scale pixmap to fit the label while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(self.cover_image_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.cover_image_label.setPixmap(scaled_pixmap)
        else:
            self.cover_image_label.setText("Failed to load image.")

    def on_video_data_fetched(self, video_data):
        self.video_data = video_data
        self.quality_options = []

        for media in video_data:
            quality = media.get("quality")
            video_url = media.get("videoUrl", "").replace("\\/", "/")
            if quality and video_url:
                self.quality_options.append((quality, video_url))
                self.quality_combo.addItem(f"{quality}p")

        if self.quality_options:
            self.quality_combo.setEnabled(True)
            self.status_label.setText("Status: Select quality and download.")
            self.quality_combo.currentIndexChanged.connect(self.on_quality_selected)
        else:
            self.status_label.setText("Status: No quality options found.")

    def on_quality_selected(self, index):
        if index >= 0 and index < len(self.quality_options):
            self.selected_quality_url = self.quality_options[index][1]
            selected_quality = self.quality_options[index][0]
            self.status_label.setText(f"Status: {selected_quality}p selected. Click 'Download' to start.")
            self.download_button.setEnabled(True)
        else:
            self.selected_quality_url = None
            self.status_label.setText("Status: Invalid quality selection.")
            self.download_button.setEnabled(False)

    def download_video(self):
        if not self.selected_quality_url:
            self.status_label.setText("Status: No quality selected.")
            return

        selected_quality = self.quality_options[self.quality_combo.currentIndex()][0]

        self.status_label.setText(f"Status: Downloading {selected_quality}p...")
        self.download_button.setEnabled(False)
        self.quality_combo.setEnabled(False)

        self.download_thread = QtCore.QThread()
        self.download_worker = DownloadWorker(
            self.selected_quality_url,
            self.headers,
            self.cookies,
            self.video_title,
            selected_quality
        )
        self.download_worker.moveToThread(self.download_thread)

        self.download_thread.started.connect(self.download_worker.run)
        self.download_worker.progress.connect(self.update_progress)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.error.connect(self.on_error)

        self.download_worker.finished.connect(self.download_thread.quit)
        self.download_worker.finished.connect(self.download_worker.deleteLater)
        self.download_thread.finished.connect(self.download_thread.deleteLater)

        self.download_thread.start()

    def update_progress(self, percent):
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f"{percent}%")

    def on_download_finished(self, filename):
        self.status_label.setText(f"Status: Downloaded to {filename}")
        self.download_button.setEnabled(False)
        self.quality_combo.setEnabled(True)
        self.progress_label.setText("100%")
        self.progress_bar.setValue(100)

    def on_error(self, message):
        self.status_label.setText(f"Status: Error - {message}")
        self.download_button.setEnabled(True)
        self.quality_combo.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")

class FindWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(list, str, str, str)  # Added cover_image_url
    error = QtCore.pyqtSignal(str)

    def __init__(self, page_url, headers, cookies):
        super().__init__()
        self.page_url = page_url
        self.headers = headers
        self.cookies = cookies

    def run(self):
        try:
            response = requests.get(self.page_url, headers=self.headers, cookies=self.cookies)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            player_div = soup.find(id="player")
            if not player_div:
                self.error.emit("#player div not found.")
                return

            # Extract Cover Image URL
            img_tag = player_div.find('img')
            if img_tag and img_tag.get('src'):
                cover_image_url = img_tag['src'].replace("\\/", "/")
            else:
                cover_image_url = ""

            script_tag = None
            for script in player_div.find_all('script'):
                if re.search(r'flashvars_\d+', script.text):
                    script_tag = script
                    break

            if not script_tag:
                self.error.emit("No matching script with flashvars found in #player.")
                return

            json_text = re.search(r'flashvars_\d+\s*=\s*(\{.*?\});', script_tag.string, re.DOTALL)
            if not json_text:
                self.error.emit("flashvars JSON data not found.")
                return

            try:
                flashvars_data = json.loads(json_text.group(1))
            except json.JSONDecodeError as e:
                self.error.emit(f"JSON parsing error: {e}")
                return

            media_definitions = flashvars_data.get('mediaDefinitions')
            if not media_definitions:
                self.error.emit("No mediaDefinitions found in flashvars.")
                return

            last_media = media_definitions[-1]
            if not last_media.get("remote", False):
                self.error.emit("Last media item does not have remote:true.")
                return

            last_media_url = last_media.get("videoUrl", "").replace("\\/", "/")
            if not last_media_url:
                self.error.emit("Last media URL not found.")
                return

            video_title_tag = soup.select_one(".video-wrapper .title .inlineFree")
            video_title = video_title_tag.text.strip().replace(" ", " ") if video_title_tag else "video"

            self.finished.emit(media_definitions, video_title, last_media_url, cover_image_url)
        except requests.RequestException as e:
            self.error.emit(f"HTTP request error: {e}")

class VideoDataWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(list)
    error = QtCore.pyqtSignal(str)

    def __init__(self, video_url, headers, cookies):
        super().__init__()
        self.video_url = video_url
        self.headers = headers
        self.cookies = cookies

    def run(self):
        try:
            response = requests.get(self.video_url, headers=self.headers, cookies=self.cookies)
            response.raise_for_status()
            video_data = response.json()
            self.finished.emit(video_data)
        except requests.RequestException as e:
            self.error.emit(f"Error fetching video data: {e}")
        except json.JSONDecodeError as e:
            self.error.emit(f"JSON decoding error: {e}")

class DownloadWorker(QtCore.QObject):
    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    def __init__(self, download_url, headers, cookies, video_title, quality):
        super().__init__()
        self.download_url = download_url
        self.headers = headers
        self.cookies = cookies
        self.video_title = video_title
        self.quality = quality

    def run(self):
        try:
            with requests.get(self.download_url, headers=self.headers, cookies=self.cookies, stream=True) as video_response:
                video_response.raise_for_status()
                total_length = int(video_response.headers.get('content-length', 0))
                downloaded = 0
                os.makedirs("download", exist_ok=True)
                safe_title = re.sub(r'[\\/*?:"<>|]', "", self.video_title)  # Remove illegal characters
                filename = os.path.join("download", f"{safe_title}_{self.quality}p.mp4")
                with open(filename, "wb") as video_file:
                    for chunk in video_response.iter_content(chunk_size=1024):
                        if chunk:
                            video_file.write(chunk)
                            downloaded += len(chunk)
                            if total_length > 0:
                                percent_complete = int((downloaded / total_length) * 100)
                                self.progress.emit(percent_complete)
            self.finished.emit(filename)
        except requests.RequestException as e:
            self.error.emit(f"Error downloading video: {e}")

class ImageFetchWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(bytes)
    error = QtCore.pyqtSignal(str)

    def __init__(self, image_url):
        super().__init__()
        self.image_url = image_url

    def run(self):
        try:
            response = requests.get(self.image_url, stream=True)
            response.raise_for_status()
            image_data = response.content
            self.finished.emit(image_data)
        except requests.RequestException as e:
            self.error.emit(f"Error fetching image: {e}")

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DownloadHub")
        self.setGeometry(200, 200, 800, 600)
        self.init_ui()

        self.cookies = {
            "__l": "65FC75EF-42FE722901BB121A2D-9ECE1D",
            "__s": "6728CC3F-42FE722901BB876CE-1C075",
            "_ga": "GA1.1.1777442377.1730726996",
            "_ga_B39RFFWGYY": "GS1.1.1730726996.1.1.1730728319.59.0.0",
            "accessAgeDisclaimerPH": "1",
            "bs": "t6w44rd46bdjdh6nknndp2d0l8smghep",
            "bsdd": "t6w44rd46bdjdh6nknndp2d0l8smghep",
            "cookieConsent": "3",
            "entryOrigin": "VidPg-premVid",
            "etavt": "%7B%2266385e0dc12af%22%3A%221_24_2_NA%7C1%22%2C%22662c2f84c2f33%22%3A%225_2_2_pornhub.related_video.96%7C0%22%7D",
            "fg_afaf12e314c5419a855ddc0bf120670f": "27930.100000",
            "htjf-mobile": "1",
            "lvv": "984390804839735301",
            "platform": "pc",
            "sessid": "101750858070270346",
            "ss": "500721751518614168",
            "ua": "c255ff0d5d20335c36999a538b820aaa",
            "views": "6",
            "vlc": "168270359546915842",
        }

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/92.0.4515.159 Safari/537.36",
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        }

    def init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # URL Input Layout
        url_layout = QtWidgets.QHBoxLayout()
        url_layout.setSpacing(10)

        self.url_input = QtWidgets.QLineEdit(self)
        self.url_input.setPlaceholderText("Enter video URL")
        self.url_input.setMinimumHeight(30)
        self.url_input.setFont(QtGui.QFont("Poppins Medium", 10))
        url_layout.addWidget(self.url_input)

        self.add_button = QtWidgets.QPushButton("Add", self)
        self.add_button.setFixedHeight(30)
        self.add_button.setFont(QtGui.QFont("Poppins Medium", 10))
        self.add_button.clicked.connect(self.add_download_item)
        url_layout.addWidget(self.add_button)

        main_layout.addLayout(url_layout)

        # Scroll Area for Download Items
        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #121212;")

        self.download_list_widget = QtWidgets.QWidget()
        self.download_list_layout = QtWidgets.QVBoxLayout()
        self.download_list_layout.setAlignment(QtCore.Qt.AlignTop)
        self.download_list_widget.setLayout(self.download_list_layout)

        self.scroll_area.setWidget(self.download_list_widget)
        main_layout.addWidget(self.scroll_area)

        central_widget.setLayout(main_layout)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #000000;
            }
            QWidget {
                color: #FFFFFF;
                font-family: "Poppins";
                font-weight: 500;
            }
            QLineEdit {
                padding: 5px;
                border: 2px solid #FFA500;
                border-radius: 5px;
                background-color: #1E1E1E;
                color: #FFFFFF;
                font-family: "Poppins";
                font-weight: 500;
            }
            QPushButton {
                background-color: #FFA500;
                color: #1B1B1B;
                border: none;
                padding: 5px 15px;
                border-radius: 5px;
                font-family: "Poppins";
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e69500;
            }
            QPushButton:disabled {
                background-color: #666666;
            }
            QScrollArea {
                border: none;
            }
        """)

    def add_download_item(self):
        page_url = self.url_input.text().strip()
        if not page_url:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please enter a valid URL.")
            return

        download_item = DownloadItem(page_url, self.headers, self.cookies, self)
        self.download_list_layout.addWidget(download_item)
        self.url_input.clear()

def main():
    app = QtWidgets.QApplication(sys.argv)

    # Load the Poppins fonts with desired weights
    from PyQt5.QtGui import QFontDatabase, QFont

    script_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(script_dir, 'fonts')

    # List of Poppins font files to load
    font_files = [
        'Poppins-Regular.ttf',    # Weight 400
        'Poppins-Medium.ttf',     # Weight 500
        'Poppins-SemiBold.ttf'    # Weight 600
    ]

    loaded_fonts = []
    for font_file in font_files:
        font_path = os.path.join(fonts_dir, font_file)
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                family = QFontDatabase.applicationFontFamilies(font_id)[0]
                loaded_fonts.append(family)
                print(f"Loaded font: {family}")
            else:
                print(f"Failed to load font: {font_file}")
        else:
            print(f"Font file not found: {font_file}")

    if not loaded_fonts:
        print("No fonts loaded. Please check the font files.")
    else:
        # Set the default application font to Poppins with desired weight
        # Choose the desired weight: 500 (Medium) or 600 (SemiBold)
        # For example, using SemiBold
        app.setFont(QFont("Poppins SemiBold", 10))
        print("Poppins SemiBold font loaded and set as default.")

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

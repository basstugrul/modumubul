import sys
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, \
    QHBoxLayout, QFrame, QSpacerItem, QSizePolicy, QScrollArea, QTabWidget, QListWidget, QListWidgetItem
from PyQt5.QtGui import QIcon, QPixmap
import webbrowser
import sqlite3
import os
from dotenv import load_dotenv


load_dotenv()
GENIUS_API_KEY = os.getenv("GENIUS_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

class SongSearchApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ModumuBul")
        self.setGeometry(100, 100, 600, 400)
        icon_path = "C:/Users/Ertu/Desktop/png/logo-color.ico"
        self.setWindowIcon(QIcon(icon_path))

        self.keyword_input = QLineEdit(self)
        search_button = QPushButton("Şarkı Ara", self)
        search_button.clicked.connect(self.search_song)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)

        self.results_container = QWidget(self.scroll_area)
        self.results_layout = QVBoxLayout(self.results_container)

        self.scroll_area.setWidget(self.results_container)

        self.favorites_list = QListWidget(self)
        self.favorites_list.setWindowTitle("Favoriler")
        self.favorites_list.itemClicked.connect(self.play_favorite)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.addTab(self.scroll_area, "Arama Sonuçları")
        self.tab_widget.addTab(self.favorites_list, "Favoriler")

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.keyword_input)
        main_layout.addWidget(search_button)
        main_layout.addWidget(self.tab_widget)

        self.favorites = {}

        self.db_connection = sqlite3.connect('favorites.db')
        self.create_table()
        self.load_favorites()

    def create_table(self):
        with self.db_connection:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    url TEXT
                )
            ''')

    def load_favorites(self):
        with self.db_connection:
            cursor = self.db_connection.cursor()
            cursor.execute('SELECT title, url FROM favorites')
            favorites = cursor.fetchall()
            for title, url in favorites:
                self.favorites[title] = url
                item = QListWidgetItem(title)
                self.favorites_list.addItem(item)

    def search_song(self):
        keyword = self.keyword_input.text()
        self.clear_results()
        if not keyword:
            return

        headers = {"Authorization": f"Bearer {GENIUS_API_KEY}"}
        url = f"https://api.genius.com/search?q={keyword}"
        response_genius = requests.get(url, headers=headers)

        if response_genius.status_code == 200:
            data = response_genius.json()
            hits = data.get('response', {}).get('hits', [])

            for hit in hits:
                song_title = hit.get('result', {}).get('title')
                artist_name = hit.get('result', {}).get('primary_artist', {}).get('name')

                if song_title and artist_name:
                    video_url = self.get_youtube_url(f"{song_title} {artist_name}")
                    print(f"Video URL for {song_title}: {video_url}")

                    result_widget = QWidget(self)
                    result_layout = QVBoxLayout(result_widget)

                    label = QLabel(f"{song_title} - {artist_name}", result_widget)
                    result_layout.addWidget(label)

                    if video_url:
                        listen_count = self.get_youtube_listen_count(video_url)
                        listen_count_label = QLabel(f"Dinlenme Sayısı: {listen_count}", result_widget)
                        result_layout.addWidget(listen_count_label)

                    thumbnail_url = hit.get('result', {}).get('header_image_url')
                    if thumbnail_url:
                        pixmap = QPixmap()
                        pixmap.loadFromData(requests.get(thumbnail_url).content)
                        scaled_pixmap = pixmap.scaledToWidth(100)
                        thumbnail_label = QLabel(result_widget)
                        thumbnail_label.setPixmap(scaled_pixmap)
                        result_layout.addWidget(thumbnail_label)

                    listen_button = QPushButton("Dinle", result_widget)
                    listen_button.clicked.connect(lambda _, title=song_title, artist=artist_name: self.play_video(title, artist))
                    result_layout.addWidget(listen_button)

                    star_button = QPushButton("⭐", result_widget)
                    star_button.clicked.connect(lambda _, title=song_title, url=video_url: self.add_to_favorites(title, url))
                    result_layout.addWidget(star_button)

                    line = QFrame(self)
                    line.setFrameShape(QFrame.HLine)
                    line.setFrameShadow(QFrame.Sunken)
                    self.results_layout.addWidget(result_widget)
                    self.results_layout.addWidget(line)

                    spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
                    self.results_layout.addItem(spacer)

    def play_video(self, title, artist):
        search_query = f"{title} {artist} official video"
        youtube_url = f"https://www.youtube.com/watch?v={self.get_video_id(search_query)}"
        webbrowser.open(youtube_url)

    def play_favorite(self, item):
        title = item.text()
        youtube_url = self.favorites.get(title)
        if youtube_url:
            webbrowser.open(youtube_url)

    def get_video_id(self, search_query):
        response = requests.get(f"https://www.youtube.com/results", params={"search_query": search_query})
        video_id = None
        if response.status_code == 200:
            start_index = response.text.find('watch?v=') + len('watch?v=')
            end_index = response.text.find('"', start_index)
            video_id = response.text[start_index:end_index]
        return video_id

    def get_youtube_url(self, search_query):
        youtube_api_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "type": "video",
            "q": search_query,
            "key": YOUTUBE_API_KEY 
        }
        response = requests.get(youtube_api_url, params=params)
        video_url = None

        if response.status_code == 200:
            response_json = response.json()
            items = response_json.get("items", [])

            if items:
                video_id = items[0].get("id", {}).get("videoId", None)
                if video_id:
                    video_url = f"https://www.youtube.com/watch?v={video_id}"

        return video_url

    def get_youtube_listen_count(self, video_url):
        listen_count = "Bilinmiyor"
        
        if video_url is not None:
            video_id = video_url.split("v=")[1]
            youtube_api_url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "statistics",
                "id": video_id,
                "key": YOUTUBE_API_KEY
            }
            response = requests.get(youtube_api_url, params=params)
            if response.status_code == 200:
                items = response.json().get("items", [])
                if items:
                    statistics = items[0].get("statistics", {})
                    listen_count = statistics.get("viewCount", "Bilinmiyor")

        return listen_count

    def add_to_favorites(self, title, url):
        if title not in self.favorites:
            with self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute('INSERT INTO favorites (title, url) VALUES (?, ?)', (title, url))
            self.favorites[title] = url
            item = QListWidgetItem(title)
            self.favorites_list.addItem(item)
            
    def clear_results(self):
        for i in reversed(range(self.results_layout.count())):
            item = self.results_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

    def __del__(self):
        if self.db_connection:
            self.db_connection.close()

if __name__ == "__main__":
  
    app = QApplication(sys.argv)
    window = SongSearchApp()
    window.show()
    sys.exit(app.exec_())

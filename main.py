import sys
import sqlite3
import pyttsx3
import re
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QComboBox, QFrame, QGraphicsDropShadowEffect, QAbstractItemView
)


# =========================================================================
# 1. SEPARATE URDU VOICE PRONUNCIATION MODULE
# =========================================================================
class UrduVocalEngine:
    """
    Dedicated audio synthesizer module exclusively for processing
    Urdu phonetic strings natively on any hardware platform.
    """

    @staticmethod
    def isolate_clean_script(text):
        return re.sub(r'[^\u0600-\u06FF\s]', '', text).strip()

    @staticmethod
    def convert_to_spoken_phonetics(urdu_text):
        glyph_mapping = {
            'ا': 'aa', 'آ': 'aa', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ٹ': 't', 'ث': 's',
            'ج': 'j', 'چ': 'ch', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ڈ': 'd', 'ذ': 'z',
            'ر': 'r', 'ڑ': 'r', 'ز': 'z', 'ژ': 'zh', 'س': 's', 'ش': 'sh', 'ص': 's',
            'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'q',
            'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm', 'ن': 'n', 'و': 'o', 'ہ': 'h',
            'ھ': 'h', 'ی': 'ee', 'ے': 'ay', 'ِ': 'i', 'َ': 'a', 'ُ': 'u'
        }
        words = UrduVocalEngine.isolate_clean_script(urdu_text).split()
        phonetic_output = []
        for word in words:
            token = "".join(glyph_mapping.get(char, "") for char in word)
            if token:
                phonetic_output.append(token)
        return " ".join(phonetic_output) if phonetic_output else urdu_text


# =========================================================================
# 2. LEXICON CLEANING UTILITIES
# =========================================================================
def extract_single_urdu_word(raw_meaning_text):
    """
    Parses and strips long dictionary explanations to deliver ONLY
    the core isolated Urdu word or phrase for clean UI list indexing.
    """
    if not raw_meaning_text:
        return ""
    # FIXED: Cleaned up character delimiter string array syntax error
    delimiters = [r'\.', r'،', r'۔', r';', r'-', r'\(']
    split_regex = '|'.join(delimiters)
    tokens = re.split(split_regex, raw_meaning_text)
    first_clean_token = tokens[0].strip()
    return first_clean_token if first_clean_token else raw_meaning_text


# =========================================================================
# 3. BACKGROUND AUDIO PERFORMANCE THREAD (Fixes Run Loop Overlap Bug)
# =========================================================================
class IsolatedSpeechThread(QThread):
    def __init__(self):
        super().__init__()
        self.payload_text = ""
        self.is_urdu_mode = False
        self.hardware_voice_id = None

    def queue_speech_job(self, text, urdu_enabled, voice_id):
        self.payload_text = text
        self.is_urdu_mode = urdu_enabled
        self.hardware_voice_id = voice_id

    def run(self):
        try:
            player = pyttsx3.init()
            if self.is_urdu_mode:
                clean_target = extract_single_urdu_word(self.payload_text)
                spoken_text = UrduVocalEngine.convert_to_spoken_phonetics(clean_target)
                player.setProperty('rate', 130)

                available_voices = player.getProperty('voices')
                for voice in available_voices:
                    if any(token in voice.id.lower() or token in voice.name.lower() for token in
                           ['hindi', 'india', 'hi', 'ur']):
                        player.setProperty('voice', voice.id)
                        break
            else:
                spoken_text = self.payload_text
                player.setProperty('rate', 150)
                if self.hardware_voice_id:
                    player.setProperty('voice', self.hardware_voice_id)

            player.say(spoken_text)
            player.runAndWait()
            player.stop()
            del player
        except Exception as error:
            print(f"Audio Engine Processing Failure: {error}")


# =========================================================================
# 4. GLOBAL DATABASE DATA WORKER
# =========================================================================
class UnfilteredDatabaseWorker(QThread):
    data_payload_ready = pyqtSignal(list)

    def __init__(self, db_path="dictionary.db"):
        super().__init__()
        self.db_path = db_path
        self.search_term = ""
        self.translation_flow = "EN_TO_UR"

    def configure_worker(self, query, flow):
        self.search_term = query.strip()
        self.translation_flow = flow

    def run(self):
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS Favorites (word_id INTEGER PRIMARY KEY)")
            connection.commit()

            # Fetches datasets alphabetically across all columns cleanly
            if not self.search_term:
                if self.translation_flow == "EN_TO_UR":
                    sql_query = """
                        SELECT Sr, WORDS, MEANING, EXISTS(SELECT 1 FROM Favorites WHERE word_id=Words.Sr)
                        FROM Words WHERE WORDS IS NOT NULL AND WORDS != ''
                        ORDER BY WORDS ASC LIMIT 25000
                    """
                    cursor.execute(sql_query)
                else:
                    sql_query = """
                        SELECT Sr, WORDS, MEANING, EXISTS(SELECT 1 FROM Favorites WHERE word_id=Words.Sr)
                        FROM Words WHERE MEANING IS NOT NULL AND MEANING != ''
                        ORDER BY MEANING ASC LIMIT 25000
                    """
                    cursor.execute(sql_query)
            else:
                if self.translation_flow == "EN_TO_UR":
                    sql_query = """
                        SELECT Sr, WORDS, MEANING, EXISTS(SELECT 1 FROM Favorites WHERE word_id=Words.Sr)
                        FROM Words WHERE WORDS LIKE ? 
                        ORDER BY WORDS ASC LIMIT 5000
                    """
                    cursor.execute(sql_query, (f"%{self.search_term}%",))
                else:
                    sql_query = """
                        SELECT Sr, WORDS, MEANING, EXISTS(SELECT 1 FROM Favorites WHERE word_id=Words.Sr)
                        FROM Words WHERE MEANING LIKE ? 
                        ORDER BY MEANING ASC LIMIT 5000
                    """
                    cursor.execute(sql_query, (f"%{self.search_term}%",))

            queried_rows = cursor.fetchall()
            connection.close()
            self.data_payload_ready.emit(queried_rows)
        except Exception as ex:
            print(f"Database Subsystem Exception Encountered: {ex}")
            self.data_payload_ready.emit([])


# =========================================================================
# 5. CORE UI INTERFACE HOUSING PRESTIGE WORKSPACE
# =========================================================================
class DictionaryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_path = "dictionary.db"
        self.active_word_id = None
        self.tts_voice_profiles = []

        try:
            temp_engine = pyttsx3.init()
            self.tts_voice_profiles = temp_engine.getProperty('voices')
            del temp_engine
        except Exception:
            pass

        self.register_custom_fonts()
        self.assemble_ui()

        self.db_engine = UnfilteredDatabaseWorker(self.db_path)
        self.db_engine.data_payload_ready.connect(self.populate_ui_list)

        self.vocal_engine = IsolatedSpeechThread()
        self.execute_refresh()

    def register_custom_fonts(self):
        QFontDatabase.addApplicationFont("Jameel Noori Nastaleeq Kasheeda.ttf")
        QFontDatabase.addApplicationFont("Cataneo_BT.ttf")

    def assemble_ui(self):
        self.setWindowTitle("Bilingual Lexicon Application Workspace")
        self.resize(1160, 780)
        self.setMinimumSize(1020, 700)

        self.setStyleSheet("""
            QMainWindow { background-color: #050811; }
            QWidget { color: #E2E8F0; font-family: "Segoe UI", "Cataneo BT"; }
            QFrame#ControlPanel { background-color: #0A101D; border-right: 1px solid #1E293B; }
            QLineEdit { background-color: #111A2E; border: 2px solid #223554; border-radius: 10px; padding: 12px 16px; color: #F8FAFC; font-size: 14px; }
            QLineEdit:focus { border: 2px solid #06B6D4; }
            QListWidget { background-color: #0A101D; border: 1px solid #1E293B; border-radius: 12px; padding: 6px; }
            QListWidget::item { padding: 15px; border-radius: 8px; margin-bottom: 6px; background-color: #111A2E; border: 1px solid #1E293B; }
            QListWidget::item:hover { background-color: #1E293B; color: #22D3EE; border: 1px solid #06B6D4; }
            QListWidget::item:selected { background-color: #06B6D4; color: #050811; font-weight: bold; }
            QPushButton { background-color: #111A2E; border: 1px solid #223554; border-radius: 8px; padding: 12px 20px; font-weight: 600; color: #F8FAFC; }
            QPushButton:hover { background-color: #1E293B; border: 1px solid #06B6D4; }
            QPushButton#ActionBtn, QPushButton#FavToggleBtn { background-color: #06B6D4; color: #050811; border: none; }
            QPushButton#ActionBtn:hover, QPushButton#FavToggleBtn:hover { background-color: #22D3EE; }
            QComboBox { background-color: #111A2E; border: 1px solid #223554; border-radius: 8px; padding: 8px; color: #F8FAFC; }
        """)

        container_widget = QWidget()
        self.setCentralWidget(container_widget)
        main_layout = QHBoxLayout(container_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("ControlPanel")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 35, 20, 35)
        sidebar_layout.setSpacing(20)

        branding_title = QLabel("LEXICON SYSTEM")
        branding_title.setStyleSheet("font-size: 18px; font-weight: 900; color: #06B6D4; letter-spacing: 2px;")
        sidebar_layout.addWidget(branding_title)

        self.translation_flow_box = QComboBox()
        self.translation_flow_box.addItems(["English ➔ Urdu", "Urdu ➔ English"])
        self.translation_flow_box.currentIndexChanged.connect(self.on_flow_mode_toggled)
        sidebar_layout.addWidget(QLabel("Active Translation Stream"))
        sidebar_layout.addWidget(self.translation_flow_box)

        sidebar_layout.addWidget(QLabel("English Pronunciation Accent"))
        self.voice_accent_box = QComboBox()
        for voice in self.tts_voice_profiles:
            self.voice_accent_box.addItem(voice.name, voice.id)
        sidebar_layout.addWidget(self.voice_accent_box)

        sidebar_layout.addStretch()

        self.btn_bookmarks_view = QPushButton("⭐ Bookmarked Terms")
        self.btn_bookmarks_view.clicked.connect(self.load_favorites_view)
        sidebar_layout.addWidget(self.btn_bookmarks_view)

        main_layout.addWidget(sidebar)

        dashboard_workspace = QWidget()
        dashboard_layout = QHBoxLayout(dashboard_workspace)
        dashboard_layout.setContentsMargins(25, 25, 25, 25)
        dashboard_layout.setSpacing(25)

        list_stack = QVBoxLayout()
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search full data records cleanly from A to Z...")
        self.search_field.textChanged.connect(self.execute_refresh)
        list_stack.addWidget(self.search_field)

        self.ui_list_widget = QListWidget()
        self.ui_list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.ui_list_widget.itemSelectionChanged.connect(self.on_list_item_activated)
        list_stack.addWidget(self.ui_list_widget)
        dashboard_layout.addLayout(list_stack, stretch=2)

        self.data_viewer_card = QFrame()
        self.data_viewer_card.setStyleSheet(
            "QFrame { background-color: #0A101D; border: 1px solid #1E293B; border-radius: 16px; }")

        drop_shadow = QGraphicsDropShadowEffect()
        drop_shadow.setBlurRadius(30)
        drop_shadow.setColor(QColor(0, 0, 0, 220))
        drop_shadow.setOffset(0, 8)
        self.data_viewer_card.setGraphicsEffect(drop_shadow)

        viewer_layout = QVBoxLayout(self.data_viewer_card)
        viewer_layout.setContentsMargins(35, 40, 35, 40)
        viewer_layout.setSpacing(25)

        self.lbl_display_word = QLabel("Lexicon Master Hub")
        self.lbl_display_word.setStyleSheet("font-size: 34px; font-weight: bold; color: #06B6D4;")
        self.lbl_display_word.setWordWrap(True)
        viewer_layout.addWidget(self.lbl_display_word)

        self.lbl_display_meaning = QLabel(
            "Select an indexed word record from the list workspace matrix row to view meanings.")
        self.lbl_display_meaning.setStyleSheet("font-size: 24px; line-height: 1.8; color: #94A3B8;")
        self.lbl_display_meaning.setWordWrap(True)
        viewer_layout.addWidget(self.lbl_display_meaning)

        viewer_layout.addStretch()

        interactive_row = QHBoxLayout()
        self.btn_trigger_speech = QPushButton("🔊 Listen Pronunciation")
        self.btn_trigger_speech.setObjectName("ActionBtn")
        self.btn_trigger_speech.clicked.connect(self.fire_vocal_synthesis)
        interactive_row.addWidget(self.btn_trigger_speech)

        self.btn_bookmark_action = QPushButton("☆ Save Word")
        self.btn_bookmark_action.setObjectName("FavToggleBtn")
        self.btn_bookmark_action.clicked.connect(self.toggle_item_bookmark)
        interactive_row.addWidget(self.btn_bookmark_action)

        viewer_layout.addLayout(interactive_row)
        dashboard_layout.addWidget(self.data_viewer_card, stretch=3)

        main_layout.addWidget(dashboard_workspace)

    def on_flow_mode_toggled(self):
        self.search_field.clear()
        if self.translation_flow_box.currentIndex() == 1:
            self.ui_list_widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self.search_field.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.search_field.setPlaceholderText("یہاں اردو لفظ تلاش کریں...")
        else:
            self.ui_list_widget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            self.search_field.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.search_field.setPlaceholderText("Search full data records cleanly from A to Z...")
        self.execute_refresh()

    def execute_refresh(self):
        flow_target = "EN_TO_UR" if self.translation_flow_box.currentIndex() == 0 else "UR_TO_EN"
        self.db_engine.configure_worker(self.search_field.text(), flow_target)
        if not self.db_engine.isRunning():
            self.db_engine.start()

    def populate_ui_list(self, records_list):
        self.ui_list_widget.clear()
        # FIXED: Tracking set filters duplicate display elements flawlessly at UI load layer
        seen_words = set()

        for row in records_list:
            sr, word, meaning, is_saved = row

            if self.translation_flow_box.currentIndex() == 0:
                if word.lower() in seen_words:
                    continue
                seen_words.add(word.lower())
                item_node = QListWidgetItem(word)
                item_node.setFont(QFont("Segoe UI", 14))
            else:
                clean_urdu_target = extract_single_urdu_word(meaning)
                if clean_urdu_target in seen_words or not clean_urdu_target:
                    continue
                seen_words.add(clean_urdu_target)
                item_node = QListWidgetItem(clean_urdu_target)
                item_node.setFont(QFont("Jameel Noori Nastaleeq Kasheeda", 19))
                item_node.setTextAlignment(Qt.AlignmentFlag.AlignRight)

            item_node.setData(Qt.ItemDataRole.UserRole, (sr, word, meaning, is_saved))
            self.ui_list_widget.addItem(item_node)

    def on_list_item_activated(self):
        selected_nodes = self.ui_list_widget.selectedItems()
        if not selected_nodes:
            return

        sr, word, meaning, is_saved = selected_nodes[0].data(Qt.ItemDataRole.UserRole)
        self.active_word_id = sr

        self.card_pop_animation = QPropertyAnimation(self.data_viewer_card, b"maximumSize")
        self.card_pop_animation.setDuration(150)
        self.card_pop_animation.setStartValue(QSize(self.data_viewer_card.width() - 12, self.data_viewer_card.height()))
        self.card_pop_animation.setEndValue(QSize(self.data_viewer_card.width(), self.data_viewer_card.height()))
        self.card_pop_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.card_pop_animation.start()

        if self.translation_flow_box.currentIndex() == 0:
            self.lbl_display_word.setText(word)
            self.lbl_display_word.setFont(QFont("Segoe UI", 28))
            self.lbl_display_word.setAlignment(Qt.AlignmentFlag.AlignLeft)

            self.lbl_display_meaning.setText(meaning)
            self.lbl_display_meaning.setFont(QFont("Jameel Noori Nastaleeq Kasheeda", 26))
            self.lbl_display_meaning.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            self.lbl_display_word.setText(extract_single_urdu_word(meaning))
            self.lbl_display_word.setFont(QFont("Jameel Noori Nastaleeq Kasheeda", 32))
            self.lbl_display_word.setAlignment(Qt.AlignmentFlag.AlignRight)

            self.lbl_display_meaning.setText(
                f"English Target Translation:\n{word}\n\nComprehensive Lexicon Context:\n{meaning}")
            self.lbl_display_meaning.setFont(QFont("Segoe UI", 18))
            self.lbl_display_meaning.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.btn_bookmark_action.setText("★ Saved" if is_saved else "☆ Save Word")

    def fire_vocal_synthesis(self):
        if not self.active_word_id:
            return

        active_selections = self.ui_list_widget.selectedItems()
        if active_selections:
            sr, word, meaning, is_saved = active_selections[0].data(Qt.ItemDataRole.UserRole)

            if self.vocal_engine.isRunning():
                self.vocal_engine.terminate()
                self.vocal_engine.wait()

            if self.translation_flow_box.currentIndex() == 0:
                self.vocal_engine.queue_speech_job(word, False, self.voice_accent_box.currentData())
            else:
                self.vocal_engine.queue_speech_job(meaning, True, None)

            self.vocal_engine.start()

    def toggle_item_bookmark(self):
        if not self.active_word_id:
            return
        db_conn = sqlite3.connect(self.db_path)
        db_cursor = db_conn.cursor()
        db_cursor.execute("SELECT 1 FROM Favorites WHERE word_id = ?", (self.active_word_id,))
        record_exists = db_cursor.fetchone()

        if record_exists:
            db_conn.execute("DELETE FROM Favorites WHERE word_id = ?", (self.active_word_id,))
            self.btn_bookmark_action.setText("☆ Save Word")
        else:
            db_conn.execute("INSERT INTO Favorites (word_id) VALUES (?)", (self.active_word_id,))
            self.btn_bookmark_action.setText("★ Saved")
        db_conn.commit()
        db_conn.close()
        self.execute_refresh()

    def load_favorites_view(self):
        try:
            db_conn = sqlite3.connect(self.db_path)
            db_cursor = db_conn.cursor()
            db_cursor.execute(
                "SELECT Words.Sr, Words.WORDS, Words.MEANING, 1 FROM Words JOIN Favorites ON Words.Sr = Favorites.word_id")
            saved_rows = db_cursor.fetchall()
            db_conn.close()
            self.populate_ui_list(saved_rows)
        except Exception as e:
            print(f"Error rendering bookmarks view index layer: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DictionaryApp()
    window.show()
    sys.exit(app.exec())
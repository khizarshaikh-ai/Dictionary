# 📚 Bilingual Lexicon Application Workspace

A premium, high-performance offline **English-Urdu and Urdu-English Dictionary** desktop application built using Python 3 and PyQt6. The application leverages a multi-threaded database worker and an intelligent custom text-to-speech phonetic processor.

---

## ✨ Key Features

* **Bi-directional Stream Mapping:** Smoothly switch between English ➔ Urdu and Urdu ➔ English search matrices.
* **Smart Duplication Filter:** Application-layer data streaming ensures completely clean, indexed rows from A to Z with no duplicate word loops.
* **Isolated Audio Subsystem:** Multi-threaded `pyttsx3` voice performance prevents UI freezing during pronunciation playback.
* **Urdu Phonetic Vocal Engine:** A custom-engineered phonetic mapping layout that isolates Urdu script, converts it to localized spoken tokens, and plays native pronunciations on any platform.
* **Modern Cyber-Obsidian UI:** High-contrast dark workspace featuring dynamic list rendering, sleek drop-shadow geometry effects, and elastic layout scale animations.
* **Personal Bookmarks Matrix:** Bookmark and save specific vocabulary words locally into a persistent storage system.

---

## 🛠️ Tech Stack & Architecture

* **Frontend Framework:** PyQt6 (Qt Widget toolkit)
* **Storage Layer:** SQLite3 (Embedded database driver)
* **Speech Synthesis Engine:** Pyttsx3 (Native OS audio bridge)
* **Typography:** Jameel Noori Nastaleeq & Cataneo BT font structures

---

## 🚀 Getting Started

### Prerequisites
Make sure you have Python 3.10+ installed on your computer.

### 1. Clone the Workspace
```bash
git clone [https://github.com/your-username/Bilingual-Lexicon-Dictionary.git](https://github.com/your-username/Bilingual-Lexicon-Dictionary.git)
cd Bilingual-Lexicon-Dictionary

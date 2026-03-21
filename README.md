# Yuki — Universal Media Downloader & MP3 Suite

```
  ██    ██ ██    ██ ██   ██ ██
   ██  ██  ██    ██ ██  ██  ██
    ████   ██    ██ █████   ██
     ██    ██    ██ ██  ██  ██
     ██     ██████  ██   ██ ██
```

**Yuki** is a professional-grade Windows desktop application for downloading media from virtually any platform — and editing MP3 metadata with ease.

---

## ✨ Features

- 🎵 **Download audio** (MP3) at up to 320kbps from YouTube, SoundCloud, TikTok, and more
- 🎬 **Download video** (MP4) up to 1080p from YouTube, Instagram, Reddit, Vimeo, and more
- 🎧 **Spotify support** — match and download Spotify tracks, albums, and playlists via YouTube
- 📝 **MP3 tag editor** — edit title, artist, album, cover art, BPM, genre, and more
- 🎛️ **Built-in audio player** — seekbar, volume control, history navigation
- 📋 **Download queue** — up to 3 concurrent downloads with progress bars
- 🗂️ **Download history** — searchable, exportable to CSV
- 🌍 **7 languages** — English, German, Turkish, Japanese, French, Spanish, Italian
- 🌙 **Dark/Light/System theme**
- 🔄 **Auto-updates yt-dlp** on startup
- 🚀 **Start with Windows** option

---

## 🌐 Supported Platforms

| Platform | Video | Audio | Playlist |
|---|---|---|---|
| YouTube | ✅ | ✅ | ✅ |
| YouTube Shorts | ✅ | ✅ | — |
| Spotify | — | ✅ | ✅ |
| Instagram | ✅ | — | — |
| TikTok | ✅ | ✅ | — |
| Twitter/X | ✅ | — | — |
| SoundCloud | — | ✅ | ✅ |
| Facebook | ✅ | — | — |
| Vimeo | ✅ | ✅ | — |
| Dailymotion | ✅ | ✅ | — |
| Twitch (clips) | ✅ | — | — |
| Reddit | ✅ | — | — |
| + Many more via yt-dlp | ✅ | ✅ | — |

---

## 🖥️ Installation (End Users)

1. Download `Yuki-Setup-1.0.0.exe` from [Releases](https://github.com/lfl1337/Yuki/releases)
2. Run the installer — choose install folder, optional desktop shortcut
3. Launch **Yuki** from the Start Menu or Desktop
4. Paste a link and hit Download!

> **Note:** Yuki bundles ffmpeg — no additional installs required.

---

## 🛠️ Developer Setup

```bash
# Clone the repo
git clone https://github.com/lfl1337/Yuki.git
cd Yuki

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download ffmpeg (place ffmpeg.exe and ffprobe.exe in /ffmpeg folder)
# https://www.gyan.dev/ffmpeg/builds/ → ffmpeg-release-essentials.zip

# Run the app
python main.py
```

---

## 🔨 Build

```bash
# Build standalone .exe
build.bat

# Output: dist\Yuki.exe
```

### Creating the Installer (requires NSIS)

```bash
makensis installer.nsi
# Output: Yuki-Setup-1.0.0.exe
```

---

## 📦 Tech Stack

| Component | Library |
|---|---|
| UI Framework | customtkinter |
| Download Engine | yt-dlp |
| Spotify | spotdl |
| Audio Metadata | mutagen |
| Image Processing | Pillow |
| Audio Playback | pygame |
| HTTP Requests | requests |
| Build | PyInstaller |
| Installer | NSIS |

---

## 📁 Project Structure

```
yuki/
├── main.py              # Entry point
├── config.py            # Constants & paths
├── ui/                  # UI components
│   ├── main_window.py
│   ├── downloader_tab.py
│   ├── history_tab.py
│   ├── editor_tab.py
│   ├── player_bar.py
│   ├── queue_panel.py
│   ├── settings_window.py
│   └── widgets/
├── core/                # Business logic
│   ├── downloader.py
│   ├── tagger.py
│   ├── player.py
│   ├── history.py
│   ├── detector.py
│   ├── updater.py
│   └── autostart.py
├── locales/             # Translations (7 languages)
├── assets/              # Icons & images
└── ffmpeg/              # Bundled ffmpeg binaries
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 🔗 Links

- **GitHub:** [github.com/lfl1337/Yuki](https://github.com/lfl1337/Yuki)
- **Issues:** [github.com/lfl1337/Yuki/issues](https://github.com/lfl1337/Yuki/issues)
- **yt-dlp:** [github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)

# Yuki — Media Suite

![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)
![Windows](https://img.shields.io/badge/Platform-Windows-blue)
![Version](https://img.shields.io/badge/version-1.0.0-purple)

> Download music and videos from YouTube, Spotify, TikTok, Instagram
> and 1000+ other platforms. Edit MP3 tags, convert between any format,
> and listen directly in the app.

## Download

Go to [Releases](https://github.com/lfl1337/Yuki/releases) and download
`Yuki_Setup_v1.0.0.exe`. Run the installer. No Python required.

## Features

- Download from YouTube, Spotify, TikTok, Instagram, SoundCloud,
  Twitter/X and 1000+ other platforms
- MP3 / MP4 download with quality selection
- Built-in MP3 tag editor (title, artist, album, cover art and more)
- Audio and video converter (MP3, WAV, FLAC, OGG, AAC, MP4, MKV and more)
- Download queue with progress bars
- Download history with search and filters
- Built-in audio player
- Multi-language support (EN, DE, TR, JA, FR, ES, IT)
- Dark / Light / System theme
- Auto-updates yt-dlp on startup

## Screenshots

Screenshots coming soon.

## Supported Platforms

YouTube, Spotify, Instagram, TikTok, SoundCloud, Twitter/X, Facebook,
Vimeo, Dailymotion, Twitch, Reddit and everything yt-dlp supports.

## Developer Setup

    git clone https://github.com/lfl1337/Yuki.git
    cd Yuki
    pip install -r requirements.txt
    Place ffmpeg.exe and ffprobe.exe in /ffmpeg/
    python main.py

## Build

    build.bat              - builds Yuki.exe via PyInstaller
    makensis installer.nsi - builds Yuki_Setup_vX.X.X.exe
    release.bat            - bumps version, builds, pushes, creates GitHub Release

## Tech Stack

Python, CustomTkinter, yt-dlp, spotdl, mutagen, pygame, ffmpeg, PyInstaller

## Author

ninym

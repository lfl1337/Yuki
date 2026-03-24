"""
Scrollable download queue panel.
Manages download tasks with threading and progress callbacks.
"""

import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional
import uuid

import customtkinter as ctk

from config import MAX_CONCURRENT_DOWNLOADS
from core.downloader import Downloader
from core.detector import detect_platform
from locales.translator import t
from ui.widgets.progress_item import ProgressItem


class DownloadTask:
    def __init__(self, task_id: str, url: str, output_dir: str,
                 fmt: str, quality: str, info: dict):
        self.id = task_id
        self.url = url
        self.output_dir = output_dir
        self.fmt = fmt
        self.quality = quality
        self.info = info
        self.downloader: Optional[Downloader] = None
        self.cancel_event = threading.Event()
        self.status = "queued"


class QueuePanel(ctk.CTkScrollableFrame):
    """
    Scrollable list of ProgressItem widgets.
    Manages a thread pool of up to MAX_CONCURRENT_DOWNLOADS workers.
    """

    def __init__(self, master, on_download_complete: Optional[Callable] = None, **kwargs):
        kwargs.pop("label_text", None)
        super().__init__(master, **kwargs)
        self._on_complete = on_download_complete or (lambda task, fp, meta: None)
        self._tasks: Dict[str, DownloadTask] = {}
        self._widgets: Dict[str, ProgressItem] = {}
        self._semaphore = threading.Semaphore(MAX_CONCURRENT_DOWNLOADS)
        self._lock = threading.Lock()

        self._empty_label = ctk.CTkLabel(
            self,
            text=t("queue_empty"),
            text_color="gray50",
            font=ctk.CTkFont(size=13),
        )
        self._empty_label.pack(pady=40)

    def add_task(self, url: str, output_dir: str, fmt: str, quality: str, info: dict):
        """Add a download task to the queue and start it when a slot is free."""
        task_id = str(uuid.uuid4())
        task = DownloadTask(task_id, url, output_dir, fmt, quality, info)
        with self._lock:
            self._tasks[task_id] = task

        title = info.get("title", url)
        platform = info.get("platform", "")
        thumb_url = info.get("thumbnail_url", "")

        widget = ProgressItem(
            self,
            title=title,
            platform=platform,
            fmt=fmt,
            quality=quality,
            thumbnail_url=thumb_url,
            on_cancel=lambda: self._cancel_task(task_id),
            on_retry=lambda: self._retry_task(task_id),
        )
        widget.pack(fill="x", padx=8, pady=4)
        with self._lock:
            self._widgets[task_id] = widget

        self._empty_label.pack_forget()

        # Launch in background thread
        thread = threading.Thread(
            target=self._run_task,
            args=(task,),
            daemon=True,
            name=f"download-{task_id[:8]}",
        )
        thread.start()

    def _run_task(self, task: DownloadTask):
        self._semaphore.acquire()
        try:
            if task.cancel_event.is_set():
                return
            self._set_status(task.id, "downloading")

            def on_progress(percent, speed, eta, filename):
                self._update_progress(task.id, percent, speed, eta, filename)

            def on_complete(filepath, metadata):
                self._set_status(task.id, "done")
                task.status = "done"
                self._on_complete(task, filepath, metadata)
                widget = self._widgets.get(task.id)
                if widget:
                    widget.after(3000, lambda: self._destroy_task(task.id))

            def on_error(msg):
                self._set_status(task.id, "error", msg)
                task.status = "error"

            dl = Downloader(
                progress_callback=on_progress,
                completion_callback=on_complete,
                error_callback=on_error,
            )
            task.downloader = dl

            if task.cancel_event.is_set():
                return

            platform = detect_platform(task.url).get("platform", "")
            if platform == "Spotify":
                dl.download_spotify(task.url, task.output_dir, task.quality)
            elif task.fmt == "audio":
                dl.download_audio(task.url, task.output_dir, task.quality)
            else:
                dl.download_video(task.url, task.output_dir, task.quality)
        except Exception as exc:
            self._set_status(task.id, "error", str(exc))
        finally:
            self._semaphore.release()

    def _cancel_task(self, task_id: str):
        task = self._tasks.get(task_id)
        if task:
            task.cancel_event.set()
            if task.downloader:
                task.downloader.cancel()
            self._set_status(task_id, "cancelled")
            self.after(500, lambda: self._destroy_task(task_id))

    def _retry_task(self, task_id: str):
        task = self._tasks.get(task_id)
        if not task:
            return
        task.cancel_event.clear()
        task.status = "queued"
        self._set_status(task_id, "queued")
        thread = threading.Thread(
            target=self._run_task, args=(task,), daemon=True
        )
        thread.start()

    def _update_progress(self, task_id: str, percent, speed, eta, filename):
        widget = self._widgets.get(task_id)
        if widget:
            widget.after(0, lambda: widget.update_progress(percent, speed, eta, filename))

    def _set_status(self, task_id: str, status: str, message: str = ""):
        widget = self._widgets.get(task_id)
        if widget:
            widget.after(0, lambda: widget.set_status(status, message))

    def _destroy_task(self, task_id: str):
        with self._lock:
            w = self._widgets.pop(task_id, None)
            if w:
                try:
                    w.destroy()
                except Exception:
                    pass
            self._tasks.pop(task_id, None)
        if not self._widgets:
            self._empty_label.pack(pady=40)

    def cancel_all(self):
        """Cancel all active/queued tasks."""
        for task_id in list(self._tasks.keys()):
            self._cancel_task(task_id)

    def clear_completed(self):
        to_remove = [
            tid for tid, t in self._tasks.items()
            if t.status in ("done", "cancelled", "error")
        ]
        with self._lock:
            for tid in to_remove:
                w = self._widgets.pop(tid, None)
                if w:
                    w.destroy()
                self._tasks.pop(tid, None)
        if not self._widgets:
            self._empty_label.pack(pady=40)

    def refresh_text(self):
        self._empty_label.configure(text=t("queue_empty"))

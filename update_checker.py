"""Check the latest GitHub Release without downloading or executing anything."""

from __future__ import annotations

import json
import re
import urllib.request

from PySide6.QtCore import QObject, Signal


RELEASE_API = "https://api.github.com/repos/Kaktus2889/CursorWaifu/releases/latest"
DOWNLOAD_FALLBACK = "https://github.com/Kaktus2889/CursorWaifu/releases/latest/download/CursorWaifu.exe"


class UpdateChecker(QObject):
    available = Signal(int, str, str)
    checked = Signal(bool)

    def __init__(self, current_build: int, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.current_build = current_build

    def start(self) -> None:
        from threading import Thread

        Thread(target=self._run, daemon=True, name="cursorwaifu-update-check").start()

    def _run(self) -> None:
        try:
            request = urllib.request.Request(
                RELEASE_API,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "CursorWaifu"},
            )
            with urllib.request.urlopen(request, timeout=4) as response:
                release = json.load(response)
            tag = str(release.get("tag_name", ""))
            match = re.search(r"windows-(\d+)(?:-|$)", tag)
            build = int(match.group(1)) if match else 0
            if build > self.current_build:
                url = DOWNLOAD_FALLBACK
                for asset in release.get("assets", []):
                    if str(asset.get("name", "")).lower() == "cursorwaifu.exe":
                        url = asset.get("browser_download_url", url)
                        break
                self.available.emit(build, tag, url)
            else:
                self.checked.emit(False)
        except Exception:
            self.checked.emit(False)


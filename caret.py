"""Geometry-only Windows caret observer. No keys, text, clipboard or screenshots."""
import ctypes as C
from ctypes import wintypes as W
import sys
import time


class GUIINFO(C.Structure):
    _fields_ = [("cbSize", W.DWORD), ("flags", W.DWORD),
                ("hwndActive", W.HWND), ("hwndFocus", W.HWND),
                ("hwndCapture", W.HWND), ("hwndMenuOwner", W.HWND),
                ("hwndMoveSize", W.HWND), ("hwndCaret", W.HWND), ("rcCaret", W.RECT)]


class MONITORINFO(C.Structure):
    _fields_ = [("cbSize", W.DWORD), ("rcMonitor", W.RECT),
                ("rcWork", W.RECT), ("dwFlags", W.DWORD), ("device", W.WCHAR * 32)]


class CaretObserver:
    def __init__(self):
        self.u = None
        self.previous = None
        self.active_until = 0
        if sys.platform == "win32":
            self.u = C.WinDLL("user32", use_last_error=True)
            self.u.GetGUIThreadInfo.argtypes = [W.DWORD, C.POINTER(GUIINFO)]
            self.u.GetGUIThreadInfo.restype = W.BOOL
            self.u.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]
            self.u.ClientToScreen.restype = W.BOOL
            self.u.GetForegroundWindow.restype = W.HWND
            self.u.MonitorFromPoint.argtypes = [W.POINT, W.DWORD]
            self.u.MonitorFromPoint.restype = W.HANDLE
            self.u.GetMonitorInfoW.argtypes = [W.HANDLE, C.POINTER(MONITORINFO)]
            self.u.GetMonitorInfoW.restype = W.BOOL
            if hasattr(self.u, "SetThreadDpiAwarenessContext"):
                self.u.SetThreadDpiAwarenessContext.argtypes = [W.HANDLE]
                self.u.SetThreadDpiAwarenessContext.restype = W.HANDLE

    def reset(self):
        self.previous = None
        self.active_until = 0

    def poll(self):
        """Return (physical x,y, monitor x,y,w,h,device), or None."""
        if self.u is None:
            return None
        old_context = None
        try:
            if hasattr(self.u, "SetThreadDpiAwarenessContext"):
                old_context = self.u.SetThreadDpiAwarenessContext(W.HANDLE(-4))
            info = GUIINFO()
            info.cbSize = C.sizeof(info)
            foreground = self.u.GetForegroundWindow()
            if not self.u.GetGUIThreadInfo(0, C.byref(info)) or not info.hwndCaret or info.hwndActive != foreground:
                self.reset()
                return None
            rect = info.rcCaret
            if rect.bottom <= rect.top:
                return None
            point = W.POINT(rect.left, rect.bottom)
            if not self.u.ClientToScreen(info.hwndCaret, C.byref(point)):
                return None
            key = (info.hwndCaret, point.x, point.y)
            now = time.monotonic()
            if key != self.previous:
                self.active_until = now + 5
            self.previous = key
            if now > self.active_until:
                return None
            monitor = self.u.MonitorFromPoint(point, 0)
            if not monitor:
                return None
            mi = MONITORINFO()
            mi.cbSize = C.sizeof(mi)
            if not self.u.GetMonitorInfoW(monitor, C.byref(mi)):
                return None
            r = mi.rcMonitor
            return (point.x, point.y, r.left, r.top, r.right-r.left, r.bottom-r.top, mi.device)
        except (OSError, ValueError):
            return None
        finally:
            if old_context:
                self.u.SetThreadDpiAwarenessContext(old_context)


def to_logical(sample, screens):
    """Map physical caret coordinates through the owning monitor's Qt geometry."""
    if sample is None:
        return None
    x, y, left, top, width, height, device = sample
    for screen in screens:
        if screen.name().casefold() == device.casefold() and width > 0 and height > 0:
            g = screen.geometry()
            return (g.x() + (x-left) * g.width()/width,
                    g.y() + (y-top) * g.height()/height)
    return None  # Don't guess on mixed-DPI/multi-monitor setups.

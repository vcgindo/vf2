import threading
import logging
import time
import inspect
import os

logger = logging.getLogger("auto_thread_supervisor")

# Preserve original methods
ORIGINAL_START = threading.Thread.start
ORIGINAL_RUN = threading.Thread.run
ORIGINAL_INIT = threading.Thread.__init__

_active_threads = []
_registry_lock = threading.Lock()

EXCLUDED_PATHS = {
    __file__,
    threading.__file__,
    os.path.abspath(threading.__file__.replace('.pyc', '.py')),  # compiled case
}

def patched_start(self, *args, **kwargs):
    self._registered_name = self.name or f"Thread-{id(self)}"
    self._start_time = time.time()

    # Look for the first frame that seems to be a Django view
    creator_info = "unknown"
    for frame_info in inspect.stack()[1:]:
        file_path = os.path.abspath(frame_info.filename)

        if all(excluded not in file_path for excluded in EXCLUDED_PATHS):
            if "views.py" in file_path:  # Heuristic for Django views
                view_name = frame_info.function
                view_line = frame_info.lineno
                view_file = file_path
                creator_info = f"View: {view_name}() in {view_file}:{view_line}"
                break
            elif "site-packages" not in file_path:  # fallback: user code
                creator_info = f"{frame_info.function}() in {file_path}:{frame_info.lineno}"
                break

    self._creator_info = creator_info

    with _registry_lock:
        _active_threads.append(self)

    result = ORIGINAL_START(self, *args, **kwargs)

    logger.info(
        f"[THREAD STARTED] → {self._registered_name} (ID={self.ident}), "
        f"created by: {self._creator_info}",
        extra={'thread_id': self.ident}
    )

    return result

def patched_run(self, *args, **kwargs):
    try:
        return ORIGINAL_RUN(self, *args, **kwargs)
    finally:
        # Only unregister if it hasn't already been wrapped
        if not getattr(self, "_is_wrapped_target", False):
            _unregister_thread(self)

def patched_init(self, *args, **kwargs):
    target = kwargs.get("target", None)
    if target:
        def wrapped_target(*a, **kw):
            try:
                return target(*a, **kw)
            finally:
                _unregister_thread(threading.current_thread())
        kwargs["target"] = wrapped_target
        self._is_wrapped_target = True  # Mark it so run() doesn't double-unregister
    ORIGINAL_INIT(self, *args, **kwargs)

def _unregister_thread(thread_obj):
    end_time = time.time()
    start_time = getattr(thread_obj, "_start_time", end_time)
    duration = end_time - start_time
    with _registry_lock:
        if thread_obj in _active_threads:
            _active_threads.remove(thread_obj)
    logger.info(
        f"[THREAD ENDED] → {getattr(thread_obj, '_registered_name', thread_obj.name)} "
        f"(ID={getattr(thread_obj, 'ident', 'Unknown')}) ran for {duration:.2f} seconds", 
        extra={'thread_id': getattr(thread_obj, 'ident', -1)}
    )

def apply_thread_patches():
    if threading.Thread.start != patched_start:
        threading.Thread.start = patched_start
    if threading.Thread.run != patched_run:
        threading.Thread.run = patched_run
    if threading.Thread.__init__ != patched_init:
        threading.Thread.__init__ = patched_init

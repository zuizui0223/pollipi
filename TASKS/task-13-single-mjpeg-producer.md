---
# Single MJPEG producer design notes

This draft describes the minimal changes to implement a single MJPEG/preview
producer in the TimelapseController and a bounded subscriber queue for monitor
clients. The goal is to ensure that /mjpeg streams do not open additional
Picamera2 instances or conflict with /preview or /start.

Implementation plan (task/13-single-mjpeg-producer):

1. TimelapseController: add a single in-memory latest-frame cache + producer task.
   - _monitor_thread (Optional[threading.Thread])
   - _monitor_lock (threading.Lock) separate from _camera_lock to control the
     producer lifecycle.
   - _latest_frame_bytes: Optional[bytes]
   - start_monitor_producer(): create and start a thread that captures scheduled
     images (or reads latest scheduled image) and writes to _latest_frame_bytes.
   - stop_monitor_producer(): signal thread to stop and join.

2. monitor_frames(): convert generator to stream the current _latest_frame_bytes
   repeatedly with a short sleep/wait. Each client sets preview_subscriber_count
   and the producer remains single. On first subscriber, producer is started.

3. preview_frame(): return _latest_frame_bytes if available; otherwise capture a
   single frame under _camera_lock.

4. Tests:
   - test_single_producer_start_stop: open a stream, assert preview_subscriber_count
     increments, close stream, assert it decrements and producer stops after idle.
   - test_preview_after_mjpeg: open MJPEG then call /preview and expect JPEG bytes.
   - test_slow_consumer_drop: simulate a slow consumer on monitor_frames and
     ensure the producer does not block or crash.

Note: The controller already has fields preview_subscriber_count and
preview_producer_state. We'll reuse these and add _latest_frame_bytes accordingly.

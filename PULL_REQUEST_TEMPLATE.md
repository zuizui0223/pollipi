Title: feat(13): single MJPEG producer and bounded preview cache

Problem

/mjpeg and /preview sometimes opened competing Picamera2 instances and
caused camera acquisition lifecycle errors ("Camera in Running state trying
acquire()" and "Camera __init__ sequence did not complete"). To avoid parallel
camera initialization we add a single in-process MJPEG producer which keeps
an in-memory cache of the latest emitted JPEG. /preview returns from that
cache when available, avoiding repeated camera opens.

What I changed

- Added a single MJPEG/preview producer to TimelapseController. The producer:
  - Runs in a dedicated thread and populates _latest_frame_bytes.
  - Is started on first /mjpeg subscriber and stops after a short idle.
  - Multiple /mjpeg clients share the same producer and cached frames.
- preview_frame now returns the cached frame if present, otherwise falls
  back to the last scheduled image on disk. It does not open the camera
  directly, avoiding acquisition conflicts with the capture loop.
- Added TASKS/task-13-single-mjpeg-producer.md with design notes and tests.

Testing performed

- Unit tests: None yet added to this branch. Recommend running server tests
  with POLLIPI_FAKE_CAMERA=1 locally.

Notes and follow-ups

- The producer will attempt to use controller._camera.capture_preview_bytes()
  if a camera object is attached to the controller; otherwise it prefers
  scheduled images. This keeps hardware capture minimal and under the
  controller's existing camera_lock.
- We should add tests for preview/mjpeg interaction and idle producer stop in
  packages/server/tests.

Reviewers

- @zuizui0223

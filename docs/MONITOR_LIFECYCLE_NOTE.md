# Monitor lifecycle

- While a PolliPi card is stopped, use one low-resolution live monitor for framing.
- When scheduled capture starts, release the live monitor so the high-resolution capture loop owns the camera.
- During capture, show the most recently saved scheduled JPEG and its timestamp/count instead of a live stream.
- When capture stops, return to the live monitor.

---
name: Event review UI bug
about: Track iPad/PWA bugs in the candidate event review screen
labels: bug, event-review, field-ui
---

## Symptom

Opening candidate/event review in the iPad PWA can return a UI error or fail to render candidate events.

## Expected behavior

The EVENT REVIEW screen should never crash, even if event rows are incomplete, old, missing an image, or have empty fields. It should show a safe fallback card with enough metadata for debugging.

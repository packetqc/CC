---
name: live-session
description: Live session analysis — real-time clip monitoring, frame extraction, multi-stream, capture recipes. Interactive diagnostic protocol.
user_invocable: true
---

# /live-session — Live Session Analysis

## When This Skill Fires

Triggered when `parse_prompt()` detects:
- `I'm live` — enter capture mode, pull clips, extract last frame, report
- `multi-live` — monitor multiple streams simultaneously
- `recipe` — print capture quick recipe

## Sub-Task Integration

Executes as a sub-task within the task workflow implement stage.

## Protocol

Full specification: `methodology/interactive-diagnostic.md`, Publication #2

### I'm Live Flow

1. `git pull origin <branch> --rebase`
2. Extract last frame from newest clip (`clip_2` → highest number)
3. Report: active tab, entry range, page number, log count, button states, anomalies
4. On follow-up, pull and extract again

### Multi-Live Flow

1. Scan `live/dynamic/` for all clip families
2. Extract last frame from each family's highest-numbered file
3. Report comparative state in single table
4. Flag cross-source inconsistencies immediately

### Recipe Output

Print the live capture quick recipe (OBS + stream_capture.py params).

### Clip Naming Convention

```
live/dynamic/
  clip_0.mp4, clip_1.mp4, clip_2.mp4       # Primary: UI
  uart_0.mp4, uart_1.mp4, uart_2.mp4       # Secondary: Serial terminal
  cam_0.mp4,  cam_1.mp4,  cam_2.mp4        # Tertiary: Physical board camera
```

### Live Session Directives

1. No image prints — extract data via single-frame reads
2. Start from latest clip (highest number)
3. Fast 1-frame pulls — last frame of latest clip only
4. Focus on live troubleshooting
5. Proceed with live code modifications based on UART feedback
6. No waiting — report immediately, propose fixes

### Escalation to Deep

During `I'm live`, proactively suggest `deep` analysis when detecting:
- State inconsistency between consecutive pulls
- UI elements in unexpected positions
- Data values that don't match expected progression

## Notes

- Clip mode persisted in session cache (`clip_mode`)
- `pause` enters discard mode, `resume capture` re-enters capture mode
- Tools: `live/stream_capture.py` for capture, ffmpeg for extraction

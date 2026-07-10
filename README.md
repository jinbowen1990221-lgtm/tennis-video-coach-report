# Tennis Video Coach Report

`tennis-video-coach-report` is a Codex skill for turning tennis practice videos into shareable coaching reports. It extracts frames, builds contact sheets, splits candidate rally/practice clips, creates slow-motion swing clips, and renders HTML/PNG/PDF reports.

This optimized version adds deeper technique coaching:

- stroke type identification for forehand, backhand, serve, volley, overhead, or unknown strokes
- phase-by-phase action breakdown: ready/split, unit turn, footwork/spacing, loading, forward swing, contact window, follow-through, recovery
- kinetic-chain analysis from feet and spacing through legs, hips, trunk, arm, racket path, finish, and recovery
- body-locked kinetic-chain motion clips whose joint markers and transfer highlights follow the player frame by frame
- evidence-weighted ability radar and overall movement score, recalculated from the same six video-based action metrics
- evidence-backed diagnosis with timestamps, frames, clips, visible observations, confidence notes, cues, and drills
- optional pose/skeleton overlays when the player is visible enough for MediaPipe-based support

## When To Use

Use this skill when a user provides a tennis video and asks for:

- AI tennis coaching
- forehand, backhand, volley, overhead, or serve technique review
- kinetic-chain or biomechanics analysis
- automatic rally or practice segment splitting
- slow-motion swing clips
- contact sheets and key frames
- shareable HTML, mobile PNG, or PDF reports

## Example Prompt

```text
调用 tennis-video-coach-report，分析 /path/to/tennis-video.mov。
请自动切分练习片段，提取关键帧，做正手/反手动作细节和动力链分析，
并输出 HTML、PNG、PDF 报告。
```

## Skill Layout

```text
skills/tennis-video-coach-report/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── analysis-checklist.md
│   ├── biomechanics-checklist.md
│   ├── config.example.json
│   ├── report-schema.md
│   └── requirements.txt
└── scripts/
    ├── compile_rallies.py
    ├── extract_tennis_frames.py
    ├── extract_pose_macos.swift
    ├── make_swing_clips.py
    ├── pose_overlay.py
    ├── pose_video_overlay.py
    ├── render_tennis_report.py
    └── split_rallies.py
```

## Outputs

Typical output artifacts include:

- `rally_review/rally_viewer.html`
- `rally_review/rally_index.json`
- `rally_review/rallies/*.mp4`
- `frame_index.json`
- `contact_sheets/*.jpg`
- `candidate_frames/*.jpg`
- `swing_clips/*/swing_slow_annotated.mp4`
- `generated_assets/kinetic_motion/kinetic_chain_overlay.mp4`
- `generated_assets/kinetic_motion/kinetic_chain_poster.jpg`
- `analysis.json`
- `report/index.html`
- `report/tennis-report-mobile.png`
- `report/tennis-report.pdf`

## Notes

The skill is evidence-first. It should not claim exact racket-face angle, spin, ball speed, precise 3D rotation, or injury risk unless the source footage and tooling actually support those claims.

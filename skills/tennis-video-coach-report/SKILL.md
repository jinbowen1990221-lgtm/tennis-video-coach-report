---
name: tennis-video-coach-report
description: Create shareable tennis practice video analysis reports with evidence-backed stroke mechanics and kinetic-chain coaching. Use when a user provides tennis video files or key frames and asks for AI tennis coaching, forehand/backhand/serve technique review, kinetic-chain analysis, stroke phase breakdown, automatic rally segmentation, rally review/download, compiling favorite rallies into one video, skeleton/pose overlays, slow-motion swing clips, contact sheets, HTML reports, mobile PNG reports, or PDF reports. This public skill generates standalone local artifacts only; it does not update private diaries, cloud documents, remote docs, or training ledgers.
---

# Tennis Video Coach Report

## Overview

Turn a tennis practice video into a portable coaching package: rally clips, a rally review viewer, extracted frames, contact sheets, selected key moments, optional MediaPipe skeleton overlays, early/middle/late slow-motion clips, and a mobile-friendly HTML/PNG/PDF report.

This skill is intended to behave like a practical tennis video coach, not just a clip exporter. Reports should identify the main visible stroke pattern, break representative swings into phases, explain where the kinetic chain connects or leaks, and tie every technical claim to a frame or clip. Prefer one high-value correction with evidence over a long generic fault list.

This is the public/shareable version. Keep all outputs in the requested output folder or a new local run folder. Do not write to private diary systems, cloud documents, or user-specific paths unless the user explicitly asks.

## Coaching Depth Standard

For each readable stroke, analyze only what the footage supports:

- **Stroke type**: forehand, one-handed backhand, two-handed backhand, volley, serve, overhead, or unknown.
- **Phase sequence**: ready/split step, unit turn, footwork and spacing, loading, forward swing, contact window, follow-through, recovery.
- **Kinetic chain**: feet, knees, hips, trunk, shoulder, arm, wrist/racket, and recovery timing.
- **Evidence**: each issue needs a timestamp, frame or slow-motion clip, visible observation, impact, cue, and drill.
- **Uncertainty**: state when player size, blur, camera angle, occlusion, or missing ball/contact makes a claim low-confidence.

Read `references/biomechanics-checklist.md` before writing detailed action or kinetic-chain claims. Read `references/analysis-checklist.md` before writing coaching copy. Read `references/scoring-rubric.md` before assigning any numeric score. Read `references/report-schema.md` before writing `analysis.json`.

## Video-Based Scoring Standard

Every score in the report must be based on visible action in the user's video:

- The top score is a comprehensive movement/action score, not a decorative report grade.
- Radar scores must come from readable stroke phases, key frames, slow-motion clips, or pose evidence.
- Swing-speed score means visible racket-head release quality, not measured ball speed or guessed km/h.
- If a category is not visible enough, mark it unscored/unknown instead of filling a default number.
- Store the evidence in `scoring.items[].evidence` and keep the displayed radar values aligned with those scoring items.

Do not use fixed sample values such as 80/78/79 unless the selected video evidence justifies those exact values.

## Dependencies

Required command-line tools: `ffmpeg`, `ffprobe`.

Python packages used by scripts: see `references/requirements.txt`.

When dependencies are missing, prefer an isolated environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r <skill-root>/references/requirements.txt
.venv/bin/python -m playwright install chromium
```

Use the active Python if the packages already exist. Do not install globally unless the user asks.

## Workflow

1. Resolve the video file.
   - Prefer a path the user provided.
   - If the user says the video was uploaded but gives no path, search recent `.mov`, `.mp4`, `.m4v` files in `~/Downloads`, `~/Desktop`, and the current workspace.
   - Keep the original video untouched.

2. Create a run folder.
   - Default: `<cwd>/tennis-video-analysis/<YYYY-MM-DD>-<video-stem>-<YYYYMMDD-HHMMSS>/`.
   - Store all derived files inside that folder: frames, contact sheets, pose overlays, clips, `analysis.json`, and report exports.

3. Extract frames and contact sheets.
   - Run:
     ```bash
     python3 <skill-root>/scripts/extract_tennis_frames.py <video> --outdir <run-folder>
     ```
   - Review `contact_sheets/` and `candidate_frames/`.
   - Pick 4-8 evidence moments: cover, ready/preparation, contact or near-contact, follow-through, main issue, and one positive frame.
   - Do not write a strong diagnosis before choosing the exact frame or clip that supports it.
   - For mechanics-heavy reports, pick at least one sequence that includes preparation, contact window, follow-through, and recovery. A single attractive frame is not enough for a kinetic-chain claim.

4. Split long videos into candidate rallies when requested.
   - Use this when the user has long continuous footage and wants to review rallies, save clips, or build a highlight video.
   - Choose a review mode:
     - `--mode auto`: default. Detects whether the footage looks like dense shots, practice chunks, or real rallies.
     - `--mode shot`: short 2-6 second clips for checking individual swings.
     - `--mode practice`: grouped practice chunks for coach feeding, ball-machine sessions, and repeated drills.
     - `--mode rally`: longer active-play intervals for true point/rally review.
   - Run:
     ```bash
     python3 <skill-root>/scripts/split_rallies.py <video> --outdir <run-folder>/rally_review --mode auto
     ```
   - If the user wants two browsing styles, generate both:
     ```bash
     python3 <skill-root>/scripts/split_rallies.py <video> --outdir <run-folder>/rally_review_shots --mode shot
     python3 <skill-root>/scripts/split_rallies.py <video> --outdir <run-folder>/rally_review_practice --mode practice
     ```
   - If the camera includes irrelevant motion outside the court, use a normalized crop:
     ```bash
     python3 <skill-root>/scripts/split_rallies.py <video> --outdir <run-folder>/rally_review --crop 0.05,0.20,0.95,0.95
     ```
   - Open `rally_review/rally_viewer.html`. The viewer is Chinese-first and supports favorites, playback speed buttons, and individual clip downloads.
   - If segmentation is too strict or too loose, rerun with `--sensitivity` or `--threshold`.
   - Treat automatic rally splits as candidates. Ask the user to confirm or name favorite IDs before compiling.

5. Compile favorite rallies when the user chooses clips.
   - Run:
     ```bash
     python3 <skill-root>/scripts/compile_rallies.py <run-folder>/rally_review/rally_index.json --ids 1,3,5 --out selected-rallies.mp4
     ```
   - Preserve the user's chosen order when provided.
   - If stream-copy concat fails, the script falls back to re-encoding.

6. Add skeleton overlays when useful.
   - Use skeletons for visible full-body or half-body frames. Prefer a frame where the player is not heavily occluded.
   - If multiple people are visible, crop around the player:
     ```bash
     python3 <skill-root>/scripts/pose_overlay.py <key-frame.jpg> --outdir <run-folder>/generated_assets --crop x1,y1,x2,y2 --timestamp "38.50s" --title "Pose skeleton demo"
     ```
   - The script writes full-frame overlay, crop overlay, comparison image, and JSON metadata.
   - Put the resulting paths in `analysis.json` under `pose_analysis`.

7. Create a body-locked kinetic-chain motion clip for mechanics-heavy reports.
   - Use a clean 0.8-2.0 second swing clip where the target player is readable. Crop tightly enough that the player occupies a useful part of the frame.
   - Run with a MediaPipe model when available; on macOS, `auto` also attempts the offline Apple Vision backend:
     ```bash
     python3 <skill-root>/scripts/pose_video_overlay.py <clean-swing-clip> \
       --outdir <run-folder>/generated_assets/kinetic_motion \
       --crop x1,y1,x2,y2 --model <pose_landmarker.task>
     ```
   - If automatic pose detection cannot meet the minimum frame-coverage threshold, do not display a fixed generic skeleton. Either choose a clearer/tighter clip or calibrate named body points on one inspected key frame and use the optical-flow fallback:
     ```bash
     python3 <skill-root>/scripts/pose_video_overlay.py <clean-swing-clip> \
       --outdir <run-folder>/generated_assets/kinetic_motion \
       --crop x1,y1,x2,y2 --backend tracked-seed --seed <seed-points.json>
     ```
   - Store the generated clip, poster, backend, tracked ratio, note, and limitations in `analysis.json` under `kinetic_motion`.
   - Treat `manual_seed_optical_flow` as a visual timing aid, not pose-estimation or quantitative joint-angle evidence.

8. Create slow-motion phase clips when requested or useful.
   - Use early/middle/late representative swings, preferably selected from contact sheets rather than raw thirds.
   - Run:
     ```bash
     python3 <skill-root>/scripts/make_swing_clips.py <video> --outdir <run-folder>/swing_clips \
       --event "early|31.75|Early|issue note|next cue" \
       --event "middle|147.25|Middle|issue note|next cue" \
       --event "late|280.75|Late|issue note|next cue"
     ```
   - Merge `swing_clips/swing_clips.json` phase paths into `analysis.json`.

9. Write `analysis.json`.
   - Follow `references/report-schema.md`.
   - Read `references/analysis-checklist.md` before writing coaching claims.
   - Read `references/scoring-rubric.md` before writing `score`, `action_score`, `ability_radar`, `scoring`, or `swing_speed`.
   - Read `references/biomechanics-checklist.md` before writing `stroke_analysis`, `kinetic_chain`, or advanced technique claims.
   - Use plain coaching language. For beginners, choose one primary bottleneck and at most two secondary issues.
   - Include:
     - title, date, player, video metadata, confidence
     - one-liner and main focus
     - coach summary
     - capture quality
     - optional `stroke_analysis`
     - optional `kinetic_chain`
     - optional `action_video_analysis` when practice and shot segmentation counts should be explained below the review video
     - required evidence-backed `scoring` when any numeric score is displayed
     - optional `evidence_frames`
     - optional `confidence_notes`
     - optional `pose_analysis`
     - phase review
     - highlights
     - issues
     - next practice
     - training prescription

10. Render the report.
   - Run:
     ```bash
     python3 <skill-root>/scripts/render_tennis_report.py <run-folder>/analysis.json --outdir <run-folder>/report --pdf --png
     ```
   - If Playwright is unavailable, still deliver HTML and explain that PDF/PNG export was skipped.

## Pose Analysis Guidance

Skeleton overlays are good evidence for:

- shoulder/hip orientation during preparation
- elbow/wrist distance from the body
- whether the player is cramped at contact
- knee bend and lower-body support
- whether the player stands up too early
- finish position and follow-through completeness
- long-term comparison of the same movement pattern

Skeleton overlays are not enough for:

- exact racket face angle
- exact contact moment
- ball speed, spin, or trajectory
- precise 3D hip/shoulder rotation
- injury or medical diagnosis

State uncertainty when the player is small, blurred, occluded, or partly outside the frame. Treat pose output as an evidence layer, not the whole analysis.

## Kinetic Motion Guidance

- Put joint markers and segment lines on the detected/tracked body, not at fixed report coordinates.
- Update marker positions frame by frame. Highlight the active transfer segment from feet and knees through hips, trunk, arm, and wrist/racket-side release using actual landmark motion.
- Require a usable detection/tracking ratio before publishing the dynamic overlay. If coverage is below the threshold, omit the animated skeleton and show the original key frame with an explicit evidence note.
- Keep video text minimal. Put coaching conclusions and caveats below the video in report copy.
- When practice-mode and shot-mode segmentation are both generated, put their counts and meanings in `action_video_analysis` below the review video. Explain how the candidate groups were used; do not leave them as standalone links or unexplained statistics.
- Do not call a 2D overlay force, torque, joint load, exact racket speed, or precise 3D rotation measurement.
- For manual optical-flow fallback, disclose that the points were calibrated on a key frame and tracked in 2D.

## Rally Segmentation Guidance

The rally splitter uses motion changes to find candidate active-play intervals. It is useful for quickly reviewing long videos, but it is not a perfect tennis rules engine.

Good uses:

- isolate likely rally clips from long continuous footage
- review each clip at 0.5x, 0.75x, 1x, 1.25x, 1.5x, or 2x speed
- download individual rallies
- favorite clips and compile a highlight reel
- hand off chosen rally IDs into deeper technical analysis

Mode guidance:

- `shot` mode is best when the user wants one swing or one ball at a time.
- `practice` mode is best for lessons, coach feeding, and ball-machine sessions where several shots belong together.
- `rally` mode is best for match play or true point construction.
- `auto` mode should be the default, but keep a manual override available because camera movement, ball pickup, or coach movement can confuse motion-only detection.

Limitations:

- false positives can happen during camera movement, ball pickup, or coach movement
- false negatives can happen when the player is small or motion is subtle
- one real rally can be split into two if there is a long pause in the middle
- two nearby rallies can merge if the between-rally pause is short

Prefer a manual review step before final compilation. For important videos, do not delete the original long video or the unselected candidate clips.

## Output Standard

Deliver these files when feasible:

- `rally_review/rally_index.json` when rally splitting is requested
- `rally_review/rally_viewer.html`
- `rally_review/rallies/*.mp4`
- `selected-rallies.mp4` when favorite rallies are compiled
- `metadata.json`
- `frame_index.json`
- `contact_sheets/*.jpg`
- `candidate_frames/*.jpg`
- `generated_assets/*pose*.jpg` when pose is enabled
- `generated_assets/kinetic_motion/kinetic_chain_overlay.mp4` when dynamic kinetic-chain tracking passes quality checks
- `generated_assets/kinetic_motion/kinetic_chain_poster.jpg`
- `generated_assets/kinetic_motion/kinetic_chain_overlay.json`
- `swing_clips/*/swing_slow_annotated.mp4` when slow motion is enabled
- `swing_clips/*/freeze_annotated.jpg`
- `analysis.json`
- `report/index.html`
- `report/tennis-report-mobile.png`
- `report/tennis-report.pdf`

The default report visual style should be a blue mobile-first assessment report layout, inspired by polished education/test result reports:

- blue report background with subtle decorative assessment texture
- white rounded report sections stacked vertically
- centered light-blue section title tabs such as `测评得分`, `动作能力分项`, `技能点得分分析`, and `教练反馈`
- top score card with circular gauge, `score`, stage label, chips, headline, and coach summary
- score copy should read as a comprehensive movement/action evaluation, with kinetic-chain quality as a first-class criterion
- targeted review video or frame card clipped around the most representative problem moment
- review video should prefer a clean clip without burned-in explanatory text; put the segment summary below the video as report copy
- HTML is the source report. Measure its rendered width and height before export; PNG must capture the full page, automatically expand the canvas when horizontal overflow is detected, and PDF must use the same screen-media dimensions so sections are not clipped or split across arbitrary A4 pages.
- kinetic-chain labels on the top review card, covering footwork, hip/trunk transfer, arm release, and racket-head acceleration when visible
- icon-led diagnosis focus cards for highlight, improvement, and next step; use the bundled `assets/icons/*.svg` card icons when available, and force all icons inside colored circles to render in white
- ability radar and metric bars, including swing-speed release when evidence supports it
- swing-speed analysis module with release score, acceleration/release/deceleration notes, and coaching implication
- key moment cards tied to timestamps
- advanced insight cards for playing style, rally organization, and load/risk notes
- no footer branding or bottom app mark in public share reports

In the final response, link the HTML report, PNG, PDF, and 2-4 representative visual assets using absolute paths.

## Boundaries

- Do not update user-specific training ledgers, private cloud folders, docs, Notion, Google Drive, or any remote destination.
- Do not include private user names, paths, API tokens, or document IDs in this public skill.
- Do not overdiagnose. One actionable correction beats a long fault list.
- Do not shame the player. Use concrete, friendly coaching language.

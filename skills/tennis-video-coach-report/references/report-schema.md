# Tennis Report JSON Schema

Create `analysis.json` in the run folder, then render it with `scripts/render_tennis_report.py`.

## Minimal Schema

```json
{
  "title": "网球训练报告：正手慢半拍",
  "date": "2026-05-22",
  "player": "Player",
  "video": {
    "path": "/absolute/path/to/video.mov",
    "duration": "46.4s",
    "scene": "小场正手 / 发球机练习"
  },
  "one_liner": "问题不在不会发力，而是准备动作晚了半拍。",
  "main_focus": "提前转肩",
  "headline": "动作柔顺舒展，兼具较好的节奏韵律与回球控制力。",
  "score": 80,
  "ntrp": "约 NTRP 3.2",
  "analysis_confidence": "分析置信度 82%",
  "confidence": "medium",
  "cover_frame": "candidate_frames/candidate_03_t038.50.jpg",
  "coach_summary": [
    "球已经出来了，但拍子还没到右后方，所以你会感觉自己被球追着打。",
    "随挥比准备动作更好，说明身体已经愿意跟着球拍过去。"
  ],
  "capture_quality": [
    {
      "title": "近机位：适合看上半身和随挥",
      "timestamp": "IMG_0525 · 34.25s",
      "frame": "IMG_0525/candidate_frames/candidate_05_t034.25.jpg",
      "zoom_frame": "generated_assets/zoom_issue_recovery.jpg",
      "note": "人物占画面比例够大，能看清拍子、身体朝向和结束姿态。",
      "metrics": [
        {"label": "人物大小", "value": "好", "level": "good"},
        {"label": "拍面可见", "value": "中", "level": "warn"},
        {"label": "回位判断", "value": "好", "level": "good"}
      ]
    }
  ],
  "stroke_analysis": [
    {
      "stroke": "forehand",
      "handedness": "right",
      "representative_timestamp": "112.75s",
      "confidence": "medium",
      "summary": "主要断点在站位和准备：脚能动，但球到身前时拍子还在最后一刻找位置。",
      "phases": [
        {
          "phase": "ready_split",
          "label": "准备 / 启动",
          "timestamp": "111.50s",
          "frame": "frames_4fps/frame_0447.jpg",
          "observation": "拍面在身前，能看到等待来球，但启动稍慢。",
          "assessment": "watch",
          "cue": "球一出来，先小碎步。"
        },
        {
          "phase": "unit_turn",
          "label": "引拍 / 单元转体",
          "timestamp": "112.25s",
          "frame": "frames_4fps/frame_0450.jpg",
          "observation": "肩和拍子开始转，但完成得偏晚。",
          "assessment": "fix",
          "cue": "拍子先回家。"
        },
        {
          "phase": "contact_window",
          "label": "触球窗口",
          "timestamp": "112.75s",
          "frame": "swing_clips/middle-中段/freeze_annotated.jpg",
          "observation": "球已经到身前附近，拍子仍在最后一刻调整。",
          "assessment": "fix",
          "cue": "先找位置，再挥拍。"
        }
      ]
    }
  ],
  "kinetic_chain": {
    "summary": "第一处断点在脚步到位和引拍时机，后面才表现成手臂临时找球。",
    "overall_level": "watch",
    "segments": [
      {
        "segment": "feet_spacing",
        "label": "脚步和击球距离",
        "level": "watch",
        "evidence": "有移动和调整步，但最后一步到位偏晚。",
        "impact": "击球前时间变短，容易被球挤到。",
        "cue": "先到球旁边。"
      },
      {
        "segment": "legs_hips",
        "label": "腿髋支撑",
        "level": "good",
        "evidence": "低球时能屈膝降重心。",
        "impact": "这是继续建立稳定击球的基础。",
        "cue": "蹲住再送。"
      },
      {
        "segment": "trunk_shoulders",
        "label": "躯干和肩",
        "level": "fix",
        "evidence": "单元转体出现，但不够早。",
        "impact": "后续挥拍更容易变成手臂补救。",
        "cue": "球一出来，先转肩。"
      }
    ]
  },
  "ability_radar": [
    {"label": "准备启动", "value": 82},
    {"label": "动力链", "value": 76},
    {"label": "击球时机", "value": 81},
    {"label": "随挥收拍", "value": 84},
    {"label": "拍面控制", "value": 80},
    {"label": "身体稳定", "value": 79}
  ],
  "evidence_frames": [
    {
      "timestamp": "112.75s",
      "frame": "swing_clips/middle-中段/freeze_annotated.jpg",
      "claim": "球到身前附近时，拍子仍在最后一刻调整。",
      "confidence": "medium"
    }
  ],
  "confidence_notes": [
    "远机位能看节奏和大体动力链，但不能精确判断拍面角度。",
    "球员占画面比例偏小，触球点判断按接近窗口处理。"
  ],
  "pose_analysis": [
    {
      "timestamp": "38.50s",
      "title": "骨架识别：反手侧身与下肢支撑",
      "overlay_frame": "generated_assets/pose_demo_full.jpg",
      "comparison_frame": "generated_assets/pose_demo_side_by_side.jpg",
      "note": "用姿态估计识别肩、肘、手腕、髋、膝、脚踝等关键点，作为动作观察的辅助证据。",
      "metrics": [
        {"label": "识别点位", "value": "32 个可见点", "level": "good"},
        {"label": "适合分析", "value": "姿态 / 距离 / 重心", "level": "good"},
        {"label": "不适合单独判断", "value": "拍面角度", "level": "warn"}
      ],
      "uses": [
        "看准备时肩膀和髋部有没有侧过去。",
        "看手肘、手腕和身体之间的距离，判断是不是容易被球挤到。",
        "看膝盖弯曲和前后脚支撑，判断是否蹲住到击球后。"
      ],
      "limits": [
        "不能直接看清拍面角度。",
        "单摄像头只能近似判断身体旋转，不能当成精确 3D 角度测量。"
      ]
    }
  ],
  "problem_tracker": [
    {
      "title": "打完回中慢半拍",
      "status": "连续出现",
      "status_level": "fix",
      "meaning": "不是单拍不会打，而是每拍之间的连接慢。",
      "evidence": [
        "IMG_0523：随挥完整，但打完后有小停顿。",
        "IMG_0525：近机位能看到结束姿态停留。"
      ],
      "cue": "打完，回中，拍面回身前。"
    }
  ],
  "phase_review": [
    {
      "phase": "early",
      "label": "前段",
      "timestamp": "6.00s",
      "clip_start": "4.75s",
      "clip_end": "7.75s",
      "normal_clip": "swing_clips/early-前段/swing_normal.mp4",
      "annotated_slow_clip": "swing_clips/early-前段/swing_slow_annotated.mp4",
      "freeze_frame": "swing_clips/early-前段/freeze_annotated.jpg",
      "focus": [0.36, 0.52, 0.18, 0.22],
      "arrow": [0.66, 0.38, 0.42, 0.50],
      "change": "刚开始这一拍比较用手找球，准备动作还没有提前完成。",
      "issue": "球来之后才开始把拍子带到右后方，时间会被压缩。",
      "cue": "球一出来，先转肩。"
    },
    {
      "phase": "middle",
      "label": "中段",
      "timestamp": "18.50s",
      "annotated_slow_clip": "swing_clips/middle-中段/swing_slow_annotated.mp4",
      "freeze_frame": "swing_clips/middle-中段/freeze_annotated.jpg",
      "change": "中段开始能提前一点点，但还不是每一拍都有。",
      "cue": "拍子先回家，再等球。"
    },
    {
      "phase": "late",
      "label": "后段",
      "timestamp": "38.50s",
      "annotated_slow_clip": "swing_clips/late-后段/swing_slow_annotated.mp4",
      "freeze_frame": "swing_clips/late-后段/freeze_annotated.jpg",
      "change": "后段随挥更放松，但脚下有一点站住。",
      "cue": "打完让拍子自然过去。"
    }
  ],
  "highlights": [
    {
      "title": "随挥完整",
      "frame": "frames_4fps/frame_0155.jpg",
      "timestamp": "38.50s",
      "note": "这拍身体跟过去了，不是只用手挡球。"
    }
  ],
  "issues": [
    {
      "title": "准备动作晚了半拍",
      "frame": "frames_4fps/frame_0106.jpg",
      "timestamp": "26.25s",
      "evidence": "球已经接近身体，拍子还在找位置。",
      "impact": "击球时间被压缩，容易变成临时拉拍、手臂硬推。",
      "cue": "球一出来，先转肩。",
      "drill": "发球机慢速 30 球，只检查拍子是否提前到右后方，不追求大力。"
    }
  ],
  "next_practice": [
    "慢速 30 球：只练出球就转肩。",
    "每 10 球停一次，看拍子有没有先到右后方。",
    "先稳定节奏，再加力量。"
  ],
  "training_prescription": [
    {
      "title": "回中反射",
      "duration": "3 分钟 / 20 球",
      "why": "修正打完停住看球的习惯。",
      "steps": [
        "每打一拍，嘴里默念“回中”。",
        "拍子回到肚脐前方，脚做一个很小的调整步。",
        "不追求打深，只看下一拍前有没有准备好。"
      ],
      "success_check": "成功标准：打完 1 秒内，拍面已经回到身前。"
    }
  ],
  "social_poster": "generated_assets/tennis_diary_poster_3x4.png",
  "social_caption": "今天抓到一个小问题：正手慢半拍。不是不会打，是准备晚了。"
}
```

## Field Notes

- `confidence`: use `high`, `medium`, or `low`.
- `score`: optional 0-100 top-line report score. If omitted, the renderer derives a conservative score from confidence and kinetic-chain level.
- `headline`: optional short top-card conclusion. If omitted, the renderer uses `main_focus`.
- `ntrp`: optional display chip such as `约 NTRP 3.2`.
- `analysis_confidence`: optional display chip such as `分析置信度 82%`.
- `cover_frame`: choose a good-looking frame, not necessarily the problem frame.
- `highlights`: 1-3 items.
- `issues`: 1-3 items, but prefer one main issue for beginners.
- `phase_review`: optional but required when the user asks for early/middle/late comparison or slow-motion clips.
- `phase_review[].annotated_slow_clip`: use the output from `scripts/make_swing_clips.py`.
- `phase_review[].change`: describe the phase-to-phase difference, not just a static flaw.
- `phase_review[].focus`: optional normalized `[cx, cy, rx, ry]` for a circle. Only include after inspecting the freeze frame.
- `phase_review[].arrow`: optional normalized `[x1, y1, x2, y2]` for an arrow. Only include after inspecting the freeze frame.
- Paths may be absolute or relative to `analysis.json`.
- Keep `cue` short enough to remember while playing.
- `capture_quality`: optional shooting-quality review. Use this to tell the user which videos are fit for detailed technique and which are only fit for rhythm/positioning.
- `capture_quality[].zoom_frame`: optional crop-assisted close-up. A zoom crop helps the user see the player, but do not pretend it creates evidence that was absent from the original frame.
- `capture_quality[].metrics[].level`: use `good`, `warn`, or `bad`.
- `stroke_analysis`: optional phase-by-phase stroke mechanics. Include when the user asks for action details, biomechanics, forehand/backhand/serve diagnosis, or a non-generic technical report.
- `stroke_analysis[].stroke`: use `forehand`, `one_handed_backhand`, `two_handed_backhand`, `volley`, `serve`, `overhead`, or `unknown`.
- `stroke_analysis[].phases[].phase`: use stable ids such as `ready_split`, `unit_turn`, `footwork_spacing`, `loading`, `forward_swing`, `contact_window`, `follow_through`, and `recovery`.
- `stroke_analysis[].phases[].assessment`: use `good`, `watch`, `fix`, or `unknown`.
- `kinetic_chain`: optional body-segment analysis. Use this when there is enough video to reason about feet-to-racket sequence.
- `kinetic_chain.overall_level` and `kinetic_chain.segments[].level`: use `good`, `watch`, `fix`, or `unknown`.
- `ability_radar`: optional 3-6 item metric list for the dark mobile report radar. Each item uses `label` and numeric `value` from 0-100. If omitted, the renderer derives values from `kinetic_chain`.
- `evidence_frames`: optional claim-to-frame map. Include at least 2-4 items for mechanics-heavy reports.
- `confidence_notes`: optional report-level uncertainty bullets. Use this to explain camera limits without weakening evidence-backed claims.
- `pose_analysis`: optional pose/skeleton review. Use this when key frames have real pose-estimation overlays.
- `pose_analysis[].overlay_frame`: full-frame skeleton overlay.
- `pose_analysis[].comparison_frame`: optional original-vs-overlay or crop-vs-overlay comparison image.
- `pose_analysis[].uses`: concrete movement questions the skeleton can help answer.
- `pose_analysis[].limits`: uncertainty boundaries; never use skeleton overlays as proof for racket face angle, ball contact, or precise 3D rotation unless those are separately measured.
- `problem_tracker`: optional long-term issue cards. Use `fix` for the main issue, `watch` for occasional/secondary flaws, and `good` for improving strengths.
- `training_prescription`: optional short practice plan for visible flaws. Keep drills tiny and measurable.
- `social_poster`: optional 3:4 image for sharing.

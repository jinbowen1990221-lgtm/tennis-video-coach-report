# Video-Based Movement Scoring Rubric

All report scores must come from visible video evidence. Do not invent decorative scores to make the report look complete.

## Required Rule

Before assigning any numeric score, identify the frame or clip evidence that supports it:

- timestamp or clip path
- visible observation
- why that observation raises or lowers the score
- confidence level based on camera quality

If the video cannot show a category, mark it `unknown` or leave it unscored. Do not fill a default value.

## Score Categories

Use these six action categories for the radar when the video supports them:

1. `准备启动`
   - Looks at split step/readiness, early first move, racket preparation before the ball arrives.
   - Lower the score when preparation starts only after the ball is already close.

2. `动力链`
   - Looks at feet-to-legs-to-hips-to-trunk-to-arm sequencing.
   - Lower the score when the stroke becomes mostly arm compensation because lower body or trunk timing is late.

3. `击球时机`
   - Looks at spacing, contact window, whether the racket meets the ball in a readable front/side zone.
   - Lower the score when the player is jammed, reaching, late, or changing racket path at the last moment.

4. `挥速释放`
   - Looks at acceleration rhythm, racket-head release through the hitting zone, and whether the body creates time for speed.
   - Do not estimate exact racket speed from ordinary video. Score visible release quality, not measured km/h.

5. `随挥收拍`
   - Looks at completion of the swing, finish balance, and whether the swing decelerates naturally.
   - Lower the score when the arm stops abruptly or the finish prevents recovery.

6. `身体稳定`
   - Looks at balance, head/trunk stability, lower-body support, and recovery posture.
   - Lower the score when the player falls away, stands up too early, or cannot recover after contact.

## Numeric Bands

- 90-100: consistently visible, efficient, and repeatable across readable swings.
- 80-89: generally good, with small timing or consistency issues.
- 70-79: usable but one visible break repeatedly affects contact quality or recovery.
- 60-69: major timing/spacing/stability issue visible in several swings.
- 1-59: severe visible breakdown, or the category is barely functional in the selected sample.
- 0: unscored because video evidence is insufficient.

## Overall Score

The total score is a comprehensive movement score, not a generic player rating. Compute it from the scored action categories.

Recommended weights when all categories are visible:

- 准备启动: 18%
- 动力链: 22%
- 击球时机: 20%
- 挥速释放: 14%
- 随挥收拍: 12%
- 身体稳定: 14%

If a category is unscored because the video cannot show it, remove it from the denominator rather than guessing.

## Required JSON Shape

Prefer a `scoring` object:

```json
{
  "scoring": {
    "method": "video_evidence_weighted_movement_score",
    "overall": 80,
    "summary": "分数基于 12 个可读正手片段、3 个慢动作片段和 4 张关键帧生成。",
    "items": [
      {
        "label": "准备启动",
        "value": 80,
        "weight": 0.18,
        "evidence": ["112.75s：来球后启动明确，但引拍仍略晚。"],
        "confidence": "medium"
      }
    ]
  }
}
```

`ability_radar` may mirror `scoring.items` for renderer compatibility, but it must not contain different values from the evidence-based `scoring.items`.

## Copy Rule

When presenting scores, make clear they are video-based action scores:

- Good: "分数基于视频中可读动作片段、关键帧和慢动作观察生成。"
- Bad: "系统综合评分 80 分。" 


# Tennis Biomechanics Checklist

Use this reference when the user wants detailed technique, action mechanics, or kinetic-chain analysis. Do not load it for a simple rally clip export.

## Evidence Rules

- Identify the player and stroke type before diagnosing.
- Use a clip, not only a still frame, for timing claims such as "late preparation", "hips fire first", or "arm starts early".
- Use one visible claim per evidence item. Avoid stacking several diagnoses on one blurry frame.
- Mark `confidence` as `low` if the player is small, contact is hidden, the ball is not visible, or the camera misses the setup.
- Do not infer injury risk, exact joint load, racket face angle, spin rate, or precise 3D rotation from one normal video.

## Stroke Phase Model

For a representative groundstroke, inspect:

1. Ready and split step: base width, racket in front, eyes on feeder/opponent, landing before the ball direction is clear.
2. Unit turn: shoulders and hips turn together, non-hitting hand supports spacing, racket moves with the torso rather than only the hand.
3. Footwork and spacing: first step to the ball, small adjustment steps, distance from body, whether the player gets jammed or reaches.
4. Loading: outside leg or stance leg accepts weight, knees and hips bend enough to support the swing.
5. Forward swing: legs and trunk start the chain, hitting arm follows, racket head has natural lag instead of being forced.
6. Contact window: contact in front/side of body, head and trunk stable enough, swing path continues through the ball.
7. Follow-through: torso finishes, arm does not stop abruptly, balance stays over the base.
8. Recovery: first recovery step, racket returns to front, player is ready before the next ball.

## Kinetic Chain Checks

Score each visible segment as `good`, `watch`, `fix`, or `unknown`:

- Feet and spacing: does the player arrive early enough to hit from a balanced distance?
- Legs and ground force: does knee/hip bend create support, or is the player standing tall or collapsing?
- Hips and pelvis: do hips participate before/with the trunk, or does the arm pull the swing alone?
- Trunk and shoulders: is there a unit turn and controlled unwind, or is the chest open too early?
- Arm structure: is the elbow/wrist distance comfortable, or is the player cramped/reaching?
- Racket path: does the racket travel through the ball, or does the swing poke/chop/stop?
- Contact discipline: is the contact window in front enough for the stroke type?
- Finish and recovery: does the finish connect to the next ready position?

Write the chain as a sequence: "脚先到位 → 髋和躯干提供支撑 → 手臂跟随释放 → 打完回位". If the sequence breaks, name the first break, not every downstream symptom.

## Forehand-Specific Checks

- Unit turn starts early with the non-hitting hand helping shoulder turn.
- Racket preparation is complete before the ball enters the hitting zone.
- Contact is in front and to the side, with enough space from the body.
- The player uses the ground and trunk before the arm accelerates.
- Follow-through finishes around shoulder height or across the body without abrupt stopping.

Common forehand chain breaks:

- Late turn: ball arrives before shoulder/racket preparation is ready.
- Arm-first swing: hips and trunk stay quiet while the arm pushes.
- Jammed spacing: contact too close to the body, elbow collapses.
- Tall contact: knees straighten early, player loses low-ball support.
- Dead finish: racket stops after contact and recovery is late.

## Backhand-Specific Checks

- One-handed backhand: shoulder turn, front shoulder stability, contact in front, long hitting arm, balanced finish.
- Two-handed backhand: both hands guide the racket, shoulders turn as a unit, contact slightly in front, trunk rotation supports the swing.
- Avoid calling a backhand problem "wrist" unless the frame clearly shows wrist collapse.

## Serve-Specific Checks

Only use this section when the full serve is visible.

- Toss: consistent placement, high enough, not forcing the body to chase.
- Loading: trophy position, shoulder tilt, knee bend, weight transfer.
- Kinetic chain: legs drive upward, hips/trunk rotate, shoulder/arm/racket release later.
- Contact: high and slightly in front, balanced reach.
- Landing and recovery: lands inside court with controlled follow-through.

If toss or contact is outside the frame, keep serve analysis low-confidence and focus on visible setup or landing.

## Output Guidance

Use `stroke_analysis` for phase-by-phase observations and `kinetic_chain` for the body-segment sequence. Good report language:

- "第一处断点在站位和准备，不是在手腕。球到身前时拍子还在找位置，后面只能靠手臂补。"
- "腿有弯，但髋和躯干没有明显把力量传给手臂，所以动作看起来是在低位伸手够球。"
- "这拍值得保留：先用脚到球旁边，再降重心，击球后没有马上失去平衡。"

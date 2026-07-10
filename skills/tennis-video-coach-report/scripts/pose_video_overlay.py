#!/usr/bin/env python3
"""Generate a body-locked kinetic-chain overlay video from a tennis clip."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError as exc:
    raise SystemExit("Install pose video dependencies: python3 -m pip install opencv-python numpy") from exc


MP_NAMES = {
    0: "nose",
    11: "left_shoulder",
    12: "right_shoulder",
    13: "left_elbow",
    14: "right_elbow",
    15: "left_wrist",
    16: "right_wrist",
    23: "left_hip",
    24: "right_hip",
    25: "left_knee",
    26: "right_knee",
    27: "left_ankle",
    28: "right_ankle",
}

CONNECTIONS = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
]

GROUPS = {
    "ground": ["left_ankle", "right_ankle", "left_knee", "right_knee"],
    "hips": ["left_hip", "right_hip"],
    "trunk": ["left_shoulder", "right_shoulder"],
    "arm": ["left_elbow", "right_elbow", "left_wrist", "right_wrist"],
}


def parse_crop(raw: str | None, width: int, height: int) -> tuple[int, int, int, int]:
    if not raw:
        return 0, 0, width, height
    values = [float(part.strip()) for part in raw.split(",")]
    if len(values) != 4:
        raise SystemExit("--crop must be x1,y1,x2,y2")
    if all(0 <= value <= 1 for value in values):
        x1, y1, x2, y2 = values
        values = [x1 * width, y1 * height, x2 * width, y2 * height]
    x1, y1, x2, y2 = [int(round(value)) for value in values]
    x1, x2 = sorted((max(0, x1), min(width, x2)))
    y1, y2 = sorted((max(0, y1), min(height, y2)))
    if x2 <= x1 or y2 <= y1:
        raise SystemExit("--crop resolved to an empty region")
    return x1, y1, x2, y2


def read_frames(video: Path, crop_raw: str | None, target_fps: float) -> tuple[list[np.ndarray], float, tuple[int, int, int, int]]:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise SystemExit(f"Could not open video: {video}")
    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    crop = parse_crop(crop_raw, width, height)
    output_fps = target_fps if target_fps > 0 else min(source_fps, 20.0)
    step = max(1.0, source_fps / output_fps)
    frames: list[np.ndarray] = []
    source_index = 0
    next_sample = 0.0
    x1, y1, x2, y2 = crop
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if source_index + 1e-6 >= next_sample:
            frames.append(frame[y1:y2, x1:x2].copy())
            next_sample += step
        source_index += 1
    capture.release()
    if not frames:
        raise SystemExit("No readable frames in video")
    return frames, output_fps, crop


def confidence_value(landmark) -> float:
    visibility = float(getattr(landmark, "visibility", 1.0) or 0.0)
    presence = float(getattr(landmark, "presence", 1.0) or 0.0)
    return min(visibility, presence) if presence > 0 else visibility


def mediapipe_poses(frames: list[np.ndarray], fps: float, model: Path, confidence: float) -> list[dict]:
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
    except ImportError as exc:
        raise RuntimeError("MediaPipe is not installed") from exc

    options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=confidence,
        min_pose_presence_confidence=confidence,
        min_tracking_confidence=confidence,
    )
    poses: list[dict] = []
    with vision.PoseLandmarker.create_from_options(options) as detector:
        for index, frame in enumerate(frames):
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect_for_video(image, int(round(index * 1000.0 / fps)))
            points = {}
            if result.pose_landmarks:
                for landmark_index, name in MP_NAMES.items():
                    landmark = result.pose_landmarks[0][landmark_index]
                    score = confidence_value(landmark)
                    if score >= confidence:
                        points[name] = [float(landmark.x), float(landmark.y), score]
            poses.append(points)
    return poses


def apple_vision_poses(frames: list[np.ndarray], fps: float, confidence: float, script: Path) -> list[dict]:
    with tempfile.TemporaryDirectory(prefix="tennis-pose-") as temp_raw:
        temp = Path(temp_raw)
        frame_dir = temp / "frames"
        frame_dir.mkdir()
        for index, frame in enumerate(frames):
            cv2.imwrite(str(frame_dir / f"frame_{index:05d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        binary = temp / "extract-pose-macos"
        env = os.environ.copy()
        env["SWIFT_MODULE_CACHE_PATH"] = str(temp / "swift-cache")
        env["CLANG_MODULE_CACHE_PATH"] = str(temp / "swift-cache")
        compile_result = subprocess.run(
            ["swiftc", str(script), "-o", str(binary)],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise RuntimeError(compile_result.stderr.strip() or "Apple Vision helper failed to compile")
        result_path = temp / "pose.json"
        detect_result = subprocess.run(
            [str(binary), str(frame_dir), str(result_path), str(confidence), str(fps)],
            text=True,
            capture_output=True,
            check=False,
        )
        if detect_result.returncode != 0 or not result_path.exists():
            raise RuntimeError(detect_result.stderr.strip() or "Apple Vision pose detection failed")
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    poses = [{} for _ in frames]
    for item in payload.get("frames", []):
        index = int(item.get("frame", -1))
        if not 0 <= index < len(poses):
            continue
        poses[index] = {
            str(name): [float(point["x"]), float(point["y"]), float(point["confidence"])]
            for name, point in (item.get("points") or {}).items()
        }
    return poses


def seed_poses(frames: list[np.ndarray], seed_path: Path) -> list[dict]:
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    seed_index = max(0, min(len(frames) - 1, int(payload.get("frame", 0))))
    height, width = frames[0].shape[:2]
    names = list((payload.get("points") or {}).keys())
    if len(names) < 6:
        raise RuntimeError("Manual seed needs at least six named body points")
    seed = np.array(
        [[float(payload["points"][name][0]) * width, float(payload["points"][name][1]) * height] for name in names],
        dtype=np.float32,
    ).reshape(-1, 1, 2)
    trajectories: list[np.ndarray | None] = [None for _ in frames]
    trajectories[seed_index] = seed.copy()
    lk = dict(winSize=(31, 31), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))

    for direction in (1, -1):
        index = seed_index
        current = seed.copy()
        previous_gray = cv2.cvtColor(frames[index], cv2.COLOR_BGR2GRAY)
        while 0 <= index + direction < len(frames):
            next_index = index + direction
            next_gray = cv2.cvtColor(frames[next_index], cv2.COLOR_BGR2GRAY)
            tracked, status, error = cv2.calcOpticalFlowPyrLK(previous_gray, next_gray, current, None, **lk)
            if tracked is None:
                break
            status = status.reshape(-1).astype(bool)
            error = error.reshape(-1) if error is not None else np.zeros(len(names), dtype=np.float32)
            stable = status & (error < 35.0)
            tracked[~stable] = current[~stable]
            current = tracked
            trajectories[next_index] = current.copy()
            previous_gray = next_gray
            index = next_index

    poses: list[dict] = []
    smoothed: dict[str, np.ndarray] = {}
    for points in trajectories:
        row = {}
        if points is not None:
            for name, raw in zip(names, points.reshape(-1, 2)):
                point = np.array([raw[0] / width, raw[1] / height], dtype=np.float32)
                if name in smoothed:
                    point = smoothed[name] * 0.58 + point * 0.42
                smoothed[name] = point
                row[name] = [float(point[0]), float(point[1]), 0.55]
        poses.append(row)
    return poses


def interpolate_missing(poses: list[dict], max_gap: int = 4) -> list[dict]:
    names = sorted({name for pose in poses for name in pose})
    for name in names:
        present = [index for index, pose in enumerate(poses) if name in pose]
        for left, right in zip(present, present[1:]):
            if right - left <= 1 or right - left > max_gap:
                continue
            a = np.array(poses[left][name][:2])
            b = np.array(poses[right][name][:2])
            score = min(float(poses[left][name][2]), float(poses[right][name][2]))
            for index in range(left + 1, right):
                ratio = (index - left) / (right - left)
                point = a * (1 - ratio) + b * ratio
                poses[index][name] = [float(point[0]), float(point[1]), score * 0.9]
    return poses


def pixel_points(pose: dict, width: int, height: int) -> dict[str, tuple[int, int, float]]:
    return {
        name: (int(round(values[0] * width)), int(round(values[1] * height)), float(values[2]))
        for name, values in pose.items()
    }


def group_motion(current: dict, previous: dict, names: list[str], body_scale: float) -> float:
    distances = []
    for name in names:
        if name in current and name in previous:
            distances.append(math.dist(current[name][:2], previous[name][:2]) / max(body_scale, 1.0))
    return float(np.mean(distances)) if distances else 0.0


def body_height(points: dict) -> float:
    ys = [value[1] for value in points.values()]
    return max(40.0, max(ys) - min(ys)) if ys else 100.0


def hitting_side(points: dict, previous: dict) -> str:
    scores = {}
    for side in ("left", "right"):
        wrist = f"{side}_wrist"
        scores[side] = math.dist(points[wrist][:2], previous[wrist][:2]) if wrist in points and wrist in previous else 0.0
    return max(scores, key=scores.get)


def draw_glow_line(canvas: np.ndarray, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int], width: int) -> None:
    overlay = canvas.copy()
    cv2.line(overlay, start, end, color, width * 4, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.18, canvas, 0.82, 0, canvas)
    cv2.line(canvas, start, end, color, width, cv2.LINE_AA)


def draw_overlay(frame: np.ndarray, pose: dict, previous_pose: dict, frame_index: int) -> tuple[np.ndarray, float]:
    output = frame.copy()
    height, width = output.shape[:2]
    points = pixel_points(pose, width, height)
    previous = pixel_points(previous_pose, width, height)
    scale = body_height(points)
    motions = {key: group_motion(points, previous, names, scale) for key, names in GROUPS.items()}
    active = max(motions, key=motions.get) if max(motions.values(), default=0) > 0.002 else "ground"
    active_index = ["ground", "hips", "trunk", "arm"].index(active)
    side = hitting_side(points, previous)
    chain = [f"{side}_ankle", f"{side}_knee", f"{side}_hip", f"{side}_shoulder", f"{side}_elbow", f"{side}_wrist"]

    for a, b in CONNECTIONS:
        if a in points and b in points:
            draw_glow_line(output, points[a][:2], points[b][:2], (245, 222, 79), max(2, int(scale * 0.018)))

    stage_edge = [1, 2, 3, 5][active_index]
    for index, (a, b) in enumerate(zip(chain, chain[1:])):
        if a not in points or b not in points:
            continue
        color = (53, 222, 255) if index <= stage_edge else (255, 238, 129)
        line_width = max(3, int(scale * (0.026 if index <= stage_edge else 0.014)))
        draw_glow_line(output, points[a][:2], points[b][:2], color, line_width)

    pulse = 1.0 + 0.28 * math.sin(frame_index * 0.72)
    stage_names = GROUPS[active]
    for name, (x, y, _) in points.items():
        is_active = name in stage_names
        radius = max(4, int(scale * (0.038 if is_active else 0.026) * pulse))
        color = (41, 210, 255) if is_active else (95, 246, 255)
        glow = output.copy()
        cv2.circle(glow, (x, y), radius * 3, color, -1, cv2.LINE_AA)
        cv2.addWeighted(glow, 0.14, output, 0.86, 0, output)
        cv2.circle(output, (x, y), radius, color, -1, cv2.LINE_AA)
        cv2.circle(output, (x, y), radius + 2, (255, 255, 255), 1, cv2.LINE_AA)

    confidence = min(1.0, len(points) / 13.0)
    return output, confidence


def encode_video(frames: list[np.ndarray], fps: float, output: Path) -> None:
    height, width = frames[0].shape[:2]
    temp = output.with_name(output.stem + "_temp.mp4")
    writer = cv2.VideoWriter(str(temp), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("Could not create overlay video")
    for frame in frames:
        writer.write(frame)
    writer.release()
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        result = subprocess.run(
            [ffmpeg, "-y", "-i", str(temp), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            temp.unlink(missing_ok=True)
            return
    temp.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a body-locked kinetic-chain overlay video.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--crop", help="x1,y1,x2,y2 as pixels or normalized values")
    parser.add_argument("--fps", type=float, default=15.0)
    parser.add_argument("--backend", choices=["auto", "mediapipe", "apple-vision", "tracked-seed"], default="auto")
    parser.add_argument("--model", type=Path, help="MediaPipe pose_landmarker .task model")
    parser.add_argument("--seed", type=Path, help="Manual normalized body-point seed JSON for optical-flow fallback")
    parser.add_argument("--confidence", type=float, default=0.20)
    parser.add_argument("--min-detection-ratio", type=float, default=0.45)
    args = parser.parse_args()

    video = args.video.expanduser().resolve()
    if not video.exists():
        raise SystemExit(f"Video not found: {video}")
    outdir = args.outdir.expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    frames, fps, crop = read_frames(video, args.crop, args.fps)

    backend = args.backend
    poses: list[dict] | None = None
    errors = []
    if backend in {"auto", "mediapipe"} and args.model and args.model.expanduser().exists():
        try:
            poses = mediapipe_poses(frames, fps, args.model.expanduser().resolve(), args.confidence)
            backend = "mediapipe"
        except Exception as exc:
            errors.append(f"MediaPipe: {exc}")
            if args.backend == "mediapipe":
                raise
    if poses is None and backend in {"auto", "apple-vision"} and platform.system() == "Darwin":
        try:
            helper = Path(__file__).with_name("extract_pose_macos.swift")
            poses = apple_vision_poses(frames, fps, args.confidence, helper)
            backend = "apple_vision"
        except Exception as exc:
            errors.append(f"Apple Vision: {exc}")
            if args.backend == "apple-vision":
                raise
    detected_ratio = sum(1 for pose in poses or [] if len(pose) >= 6) / max(1, len(frames))
    if (poses is None or detected_ratio < args.min_detection_ratio) and args.seed:
        poses = seed_poses(frames, args.seed.expanduser().resolve())
        backend = "manual_seed_optical_flow"
        detected_ratio = 1.0
    if poses is None or detected_ratio < args.min_detection_ratio:
        detail = "; ".join(errors) if errors else "no usable pose backend"
        raise SystemExit(
            f"Pose detection coverage {detected_ratio:.0%} is below {args.min_detection_ratio:.0%}. "
            f"Use a tighter --crop, provide --model, or provide --seed. {detail}"
        )

    poses = interpolate_missing(poses)
    rendered = []
    frame_confidences = []
    previous_pose = poses[0] if poses and poses[0] else {}
    poster_index = 0
    poster_score = -1.0
    for index, (frame, pose) in enumerate(zip(frames, poses)):
        if not pose:
            rendered.append(frame)
            frame_confidences.append(0.0)
            continue
        overlay, score = draw_overlay(frame, pose, previous_pose, index)
        rendered.append(overlay)
        frame_confidences.append(score)
        if score > poster_score:
            poster_score = score
            poster_index = index
        previous_pose = pose

    video_path = outdir / "kinetic_chain_overlay.mp4"
    poster_path = outdir / "kinetic_chain_poster.jpg"
    metadata_path = outdir / "kinetic_chain_overlay.json"
    encode_video(rendered, fps, video_path)
    cv2.imwrite(str(poster_path), rendered[poster_index], [cv2.IMWRITE_JPEG_QUALITY, 94])
    metadata = {
        "video": str(video_path),
        "poster": str(poster_path),
        "backend": backend,
        "frame_count": len(frames),
        "fps": round(fps, 3),
        "tracked_ratio": round(detected_ratio, 4),
        "average_visible_ratio": round(float(np.mean(frame_confidences)), 4),
        "crop": list(crop),
        "source": str(video),
        "evidence_level": "pose_estimation" if backend in {"mediapipe", "apple_vision"} else "manual_seed_tracking",
        "limitations": [
            "二维单机位姿态跟踪用于观察关节时序，不代表精确三维角度或受力测量。",
            "球拍不是人体关节点，拍头路径仍需结合原视频和关键帧判断。",
        ],
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

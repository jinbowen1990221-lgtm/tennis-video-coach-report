#!/usr/bin/env python3
"""Render a beginner-friendly tennis analysis report from analysis.json."""

from __future__ import annotations

import argparse
import html
import json
import math
import shutil
import sys
from datetime import date
from pathlib import Path


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def rel_asset(frame: str | None, analysis_dir: Path, asset_dir: Path) -> str:
    if not frame:
        return ""
    src = Path(frame)
    if not src.is_absolute():
        src = analysis_dir / src
    src = src.resolve()
    if not src.exists():
        return ""
    asset_dir.mkdir(parents=True, exist_ok=True)
    name = src.name
    dst = asset_dir / name
    counter = 2
    while dst.exists() and dst.resolve() != src:
        dst = asset_dir / f"{src.stem}-{counter}{src.suffix}"
        counter += 1
    if dst.resolve() != src:
        shutil.copy2(src, dst)
    return f"assets/{dst.name}"


def rel_media(path_value: str | None, analysis_dir: Path, asset_dir: Path) -> str:
    return rel_asset(path_value, analysis_dir, asset_dir)


def image_tag(src: str, alt: str = "") -> str:
    if not src:
        return '<div class="placeholder">frame missing</div>'
    return f'<img src="{esc(src)}" alt="{esc(alt)}">'


def confidence_label(value: object) -> str:
    mapping = {
        "high": "高",
        "medium": "中",
        "low": "低",
    }
    return mapping.get(str(value or "").lower(), str(value or ""))


def render_cards(items: list[dict], kind: str, analysis_dir: Path, asset_dir: Path) -> str:
    cards = []
    for item in items:
        img = rel_asset(item.get("frame"), analysis_dir, asset_dir)
        if kind == "issue":
            body = f"""
              <p><b>看到什么</b>{esc(item.get("evidence"))}</p>
              <p><b>影响</b>{esc(item.get("impact"))}</p>
              <p><b>口令</b>{esc(item.get("cue"))}</p>
              <p><b>练习</b>{esc(item.get("drill"))}</p>
            """
        else:
            body = f"<p>{esc(item.get('note'))}</p>"
        cards.append(f"""
          <article class="moment {kind}">
            <div class="moment-img">{image_tag(img, item.get("title", ""))}</div>
            <div class="moment-body">
              <div class="time">{esc(item.get("timestamp", ""))}</div>
              <h3>{esc(item.get("title", ""))}</h3>
              {body}
            </div>
          </article>
        """)
    return "\n".join(cards)


def render_phase_review(items: list[dict], analysis_dir: Path, asset_dir: Path) -> str:
    if not items:
        return ""
    cards = []
    for item in items:
        video = rel_media(
            item.get("annotated_slow_clip") or item.get("slow_clip") or item.get("clip") or item.get("normal_clip"),
            analysis_dir,
            asset_dir,
        )
        poster = rel_asset(item.get("freeze_frame") or item.get("frame"), analysis_dir, asset_dir)
        media = ""
        if video:
            poster_attr = f' poster="{esc(poster)}"' if poster else ""
            media = f'<video controls playsinline preload="metadata"{poster_attr}><source src="{esc(video)}" type="video/mp4"></video>'
        elif poster:
            media = image_tag(poster, item.get("label", ""))
        else:
            media = '<div class="placeholder">clip missing</div>'
        detail_rows = []
        for key, label in [("change", "变化"), ("issue", "问题"), ("note", "观察"), ("cue", "口令")]:
            if item.get(key):
                detail_rows.append(f"<p><b>{label}</b>{esc(item.get(key))}</p>")
        cards.append(f"""
          <article class="phase-card">
            <div class="phase-media">{media}</div>
            <div class="phase-body">
              <div class="time">{esc(item.get("timestamp", ""))}</div>
              <h3>{esc(item.get("label") or item.get("phase") or "")}</h3>
              {''.join(detail_rows)}
            </div>
          </article>
        """)
    return f"""
    <section class="section">
      <h2>前中后变化</h2>
      <div class="phase-grid">{''.join(cards)}</div>
    </section>
    """


def render_capture_quality(items: list[dict], analysis_dir: Path, asset_dir: Path) -> str:
    if not items:
        return ""
    cards = []
    for item in items:
        raw = rel_asset(item.get("frame"), analysis_dir, asset_dir)
        zoom = rel_asset(item.get("zoom_frame"), analysis_dir, asset_dir)
        media = ""
        if raw or zoom:
            media = f"""
              <div class="quality-media">
                <div>{image_tag(raw, "原画面")}<span>原画面</span></div>
                <div>{image_tag(zoom, "人物放大")}<span>人物放大</span></div>
              </div>
            """
        metrics = "".join(
            f'<li><b>{esc(m.get("label"))}</b><span class="score {esc(m.get("level", ""))}">{esc(m.get("value"))}</span></li>'
            for m in item.get("metrics", [])
        )
        cards.append(f"""
          <article class="quality-card">
            {media}
            <div class="quality-body">
              <div class="time">{esc(item.get("timestamp", ""))}</div>
              <h3>{esc(item.get("title", ""))}</h3>
              <p>{esc(item.get("note", ""))}</p>
              <ul class="metrics">{metrics}</ul>
            </div>
          </article>
        """)
    return f"""
    <section class="section">
      <h2>拍摄质量 & 人像放大</h2>
      <div class="quality-grid">{''.join(cards)}</div>
    </section>
    """


def render_pose_analysis(items: list[dict], analysis_dir: Path, asset_dir: Path) -> str:
    if not items:
        return ""
    cards = []
    for item in items:
        overlay = rel_asset(item.get("overlay_frame"), analysis_dir, asset_dir)
        comparison = rel_asset(item.get("comparison_frame"), analysis_dir, asset_dir)
        media = ""
        if comparison:
            media = f'<div class="pose-media wide">{image_tag(comparison, item.get("title", ""))}</div>'
        elif overlay:
            media = f'<div class="pose-media">{image_tag(overlay, item.get("title", ""))}</div>'
        metrics = "".join(
            f'<li><b>{esc(m.get("label"))}</b><span class="score {esc(m.get("level", ""))}">{esc(m.get("value"))}</span></li>'
            for m in item.get("metrics", [])
        )
        uses = "".join(f"<li>{esc(use)}</li>" for use in item.get("uses", []))
        limits = "".join(f"<li>{esc(limit)}</li>" for limit in item.get("limits", []))
        blocks = ""
        if uses:
            blocks += f"<h4>能用来分析</h4><ul>{uses}</ul>"
        if limits:
            blocks += f"<h4>暂时不能替代</h4><ul>{limits}</ul>"
        cards.append(f"""
          <article class="pose-card">
            {media}
            <div class="pose-body">
              <div class="time">{esc(item.get("timestamp", ""))}</div>
              <h3>{esc(item.get("title", ""))}</h3>
              <p>{esc(item.get("note", ""))}</p>
              <ul class="metrics">{metrics}</ul>
              <div class="pose-lists">{blocks}</div>
            </div>
          </article>
        """)
    return f"""
    <section class="section">
      <h2>骨架识别分析</h2>
      <div class="pose-grid">{''.join(cards)}</div>
    </section>
    """


def level_label(value: object) -> str:
    mapping = {
        "good": "稳定",
        "watch": "观察",
        "fix": "优先修正",
        "unknown": "无法判断",
    }
    return mapping.get(str(value or "").lower(), str(value or ""))


def render_stroke_analysis(items: list[dict], analysis_dir: Path, asset_dir: Path) -> str:
    if not items:
        return ""
    cards = []
    for item in items:
        phases = []
        for phase in item.get("phases", []):
            img = rel_asset(phase.get("frame"), analysis_dir, asset_dir)
            media = image_tag(img, phase.get("label", "")) if img else ""
            phases.append(f"""
              <article class="phase-detail {esc(phase.get("assessment", ""))}">
                {f'<div class="phase-thumb">{media}</div>' if media else ''}
                <div class="phase-detail-body">
                  <div class="detail-top">
                    <span>{esc(phase.get("timestamp", ""))}</span>
                    <b>{esc(level_label(phase.get("assessment", "")))}</b>
                  </div>
                  <h4>{esc(phase.get("label") or phase.get("phase") or "")}</h4>
                  <p>{esc(phase.get("observation", ""))}</p>
                  {f'<div class="tracker-cue">{esc(phase.get("cue", ""))}</div>' if phase.get("cue") else ''}
                </div>
              </article>
            """)
        cards.append(f"""
          <article class="stroke-card">
            <div class="stroke-head">
              <div>
                <div class="time">{esc(item.get("representative_timestamp", ""))}</div>
                <h3>{esc(item.get("stroke", "stroke"))}</h3>
              </div>
              <span>{esc(confidence_label(item.get("confidence", "")))}</span>
            </div>
            <p>{esc(item.get("summary", ""))}</p>
            <div class="phase-detail-grid">{''.join(phases)}</div>
          </article>
        """)
    return f"""
    <section class="section">
      <h2>动作细节拆解</h2>
      <div class="stroke-grid">{''.join(cards)}</div>
    </section>
    """


def render_kinetic_chain(chain: dict) -> str:
    if not chain:
        return ""
    segments = []
    for segment in chain.get("segments", []):
        level = str(segment.get("level", ""))
        segments.append(f"""
          <article class="chain-segment {esc(level)}">
            <div class="chain-top">
              <strong>{esc(segment.get("label") or segment.get("segment") or "")}</strong>
              <span>{esc(level_label(level))}</span>
            </div>
            <p><b>证据</b>{esc(segment.get("evidence", ""))}</p>
            <p><b>影响</b>{esc(segment.get("impact", ""))}</p>
            {f'<div class="tracker-cue">{esc(segment.get("cue", ""))}</div>' if segment.get("cue") else ''}
          </article>
        """)
    return f"""
    <section class="section">
      <h2>动力链分析</h2>
      <article class="chain-card {esc(chain.get("overall_level", ""))}">
        <p>{esc(chain.get("summary", ""))}</p>
        <div class="chain-grid">{''.join(segments)}</div>
      </article>
    </section>
    """


def render_evidence_frames(items: list[dict], analysis_dir: Path, asset_dir: Path) -> str:
    if not items:
        return ""
    cards = []
    for item in items:
        img = rel_asset(item.get("frame"), analysis_dir, asset_dir)
        cards.append(f"""
          <article class="evidence-card">
            <div class="evidence-img">{image_tag(img, item.get("claim", ""))}</div>
            <div class="evidence-body">
              <div class="time">{esc(item.get("timestamp", ""))}</div>
              <h3>{esc(item.get("claim", ""))}</h3>
              <span>{esc(confidence_label(item.get("confidence", "")))}</span>
            </div>
          </article>
        """)
    return f"""
    <section class="section">
      <h2>证据帧</h2>
      <div class="evidence-grid">{''.join(cards)}</div>
    </section>
    """


def render_confidence_notes(items: list[str]) -> str:
    if not items:
        return ""
    rows = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f"""
    <section class="section">
      <h2>判断边界</h2>
      <div class="card confidence-notes"><ul>{rows}</ul></div>
    </section>
    """


def render_problem_tracker(items: list[dict]) -> str:
    if not items:
        return ""
    cards = []
    for item in items:
        evidence = "".join(f"<li>{esc(e)}</li>" for e in item.get("evidence", []))
        cards.append(f"""
          <article class="tracker-card {esc(item.get("status_level", ""))}">
            <div class="tracker-top">
              <span>{esc(item.get("status", ""))}</span>
              <strong>{esc(item.get("title", ""))}</strong>
            </div>
            <p>{esc(item.get("meaning", ""))}</p>
            <ul>{evidence}</ul>
            <div class="tracker-cue">{esc(item.get("cue", ""))}</div>
          </article>
        """)
    return f"""
    <section class="section">
      <h2>问题追踪卡</h2>
      <div class="tracker-grid">{''.join(cards)}</div>
    </section>
    """


def render_training_prescription(items: list[dict]) -> str:
    if not items:
        return ""
    cards = []
    for item in items:
        steps = "".join(f"<li>{esc(step)}</li>" for step in item.get("steps", []))
        cards.append(f"""
          <article class="drill-card">
            <div class="time">{esc(item.get("duration", ""))}</div>
            <h3>{esc(item.get("title", ""))}</h3>
            <p>{esc(item.get("why", ""))}</p>
            <ol>{steps}</ol>
            <div class="tracker-cue">{esc(item.get("success_check", ""))}</div>
          </article>
        """)
    return f"""
    <section class="section">
      <h2>瑕疵修正训练</h2>
      <div class="drill-grid">{''.join(cards)}</div>
    </section>
    """


def render_html(data: dict, analysis_path: Path, outdir: Path) -> str:
    analysis_dir = analysis_path.parent
    asset_dir = outdir / "assets"
    cover = rel_asset(data.get("cover_frame"), analysis_dir, asset_dir)
    video = data.get("video") or {}
    summaries = data.get("coach_summary") or []
    next_practice = data.get("next_practice") or []
    highlights = data.get("highlights") or []
    issues = data.get("issues") or []
    phase_review = data.get("phase_review") or data.get("phase_reviews") or []
    capture_quality = data.get("capture_quality") or []
    pose_analysis = data.get("pose_analysis") or []
    stroke_analysis = data.get("stroke_analysis") or []
    kinetic_chain = data.get("kinetic_chain") or {}
    evidence_frames = data.get("evidence_frames") or []
    confidence_notes = data.get("confidence_notes") or []
    problem_tracker = data.get("problem_tracker") or []
    training_prescription = data.get("training_prescription") or []
    today = data.get("date") or date.today().isoformat()

    summary_html = "".join(f"<li>{esc(s)}</li>" for s in summaries)
    practice_html = "".join(f"<li>{esc(s)}</li>" for s in next_practice)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(data.get("title", "网球训练报告"))}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #f4f1e8;
      color: #14211b;
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", Arial, sans-serif;
    }}
    .page {{
      width: min(100%, 860px);
      margin: 0 auto;
      padding: 28px 18px 42px;
    }}
    .hero {{
      position: relative;
      overflow: hidden;
      border-radius: 28px;
      min-height: 540px;
      background: #dfe6dc;
      box-shadow: 0 24px 70px rgba(20, 33, 27, .13);
    }}
    .hero img {{
      width: 100%;
      height: 620px;
      object-fit: cover;
      display: block;
      filter: brightness(1.05) contrast(.96) saturate(1.04);
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(10,20,15,0) 42%, rgba(10,20,15,.72) 100%);
    }}
    .hero-text {{
      position: absolute;
      left: 28px;
      right: 28px;
      bottom: 28px;
      z-index: 2;
      color: white;
    }}
    .kicker {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 13px;
      border-radius: 999px;
      background: rgba(255,255,255,.9);
      color: #08784f;
      font-size: 14px;
      font-weight: 800;
      margin-bottom: 14px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(38px, 9vw, 72px);
      line-height: .98;
      letter-spacing: 0;
    }}
    .one {{
      margin: 14px 0 0;
      font-size: clamp(20px, 4vw, 30px);
      line-height: 1.25;
      font-weight: 700;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin: 16px 0 24px;
    }}
    .meta div, .card, .moment, .practice {{
      background: rgba(255,255,255,.88);
      border: 1px solid rgba(20,33,27,.08);
      box-shadow: 0 16px 42px rgba(20,33,27,.08);
    }}
    .meta div {{
      border-radius: 18px;
      padding: 15px 16px;
      font-size: 15px;
      line-height: 1.25;
    }}
    .meta b {{
      display: block;
      color: #08784f;
      margin-bottom: 5px;
      font-size: 13px;
    }}
    .section {{
      margin-top: 22px;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 28px;
      line-height: 1.1;
    }}
    .card {{
      border-radius: 24px;
      padding: 22px;
    }}
    .card li, .practice li {{
      margin: 0 0 10px;
      font-size: 19px;
      line-height: 1.45;
    }}
    .moment {{
      overflow: hidden;
      border-radius: 24px;
      margin-bottom: 14px;
      display: grid;
      grid-template-columns: 44% 1fr;
    }}
    .phase-grid {{
      display: grid;
      gap: 14px;
    }}
    .phase-card {{
      overflow: hidden;
      border-radius: 24px;
      background: rgba(255,255,255,.88);
      border: 1px solid rgba(20,33,27,.08);
      box-shadow: 0 16px 42px rgba(20,33,27,.08);
    }}
    .phase-media {{
      background: #dfe6dc;
    }}
    .phase-media video,
    .phase-media img {{
      display: block;
      width: 100%;
      max-height: 520px;
      object-fit: cover;
    }}
    .phase-body {{
      padding: 18px 20px 20px;
    }}
    .phase-body p {{
      margin: 0 0 9px;
      font-size: 17px;
      line-height: 1.36;
    }}
    .phase-body p b {{
      display: inline-block;
      min-width: 46px;
      color: #08784f;
      margin-right: 6px;
    }}
    .moment-img {{
      min-height: 250px;
      background: #dfe6dc;
    }}
    .moment-img img {{
      width: 100%;
      height: 100%;
      min-height: 250px;
      object-fit: cover;
      display: block;
    }}
    .placeholder {{
      height: 100%;
      min-height: 250px;
      display: grid;
      place-items: center;
      color: #7a867d;
      font-size: 14px;
    }}
    .moment-body {{
      padding: 20px;
    }}
    .time {{
      color: #08784f;
      font-size: 13px;
      font-weight: 800;
      margin-bottom: 6px;
    }}
    h3 {{
      margin: 0 0 10px;
      font-size: 24px;
      line-height: 1.1;
    }}
    .moment p {{
      margin: 0 0 10px;
      font-size: 17px;
      line-height: 1.36;
    }}
    .moment p b {{
      display: inline-block;
      min-width: 72px;
      color: #08784f;
      margin-right: 6px;
    }}
    .practice {{
      border-radius: 24px;
      padding: 20px 22px;
    }}
    .caption {{
      margin: 18px 0 0;
      color: #66736b;
      font-size: 16px;
      line-height: 1.4;
    }}
    .quality-grid, .tracker-grid, .drill-grid {{
      display: grid;
      gap: 14px;
    }}
    .quality-card, .pose-card, .tracker-card, .drill-card {{
      background: rgba(255,255,255,.88);
      border: 1px solid rgba(20,33,27,.08);
      box-shadow: 0 16px 42px rgba(20,33,27,.08);
      border-radius: 24px;
      overflow: hidden;
    }}
    .quality-media {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1px;
      background: rgba(20,33,27,.1);
    }}
    .quality-media div {{
      position: relative;
      background: #dfe6dc;
      min-height: 260px;
    }}
    .quality-media img {{
      width: 100%;
      height: 100%;
      min-height: 260px;
      object-fit: cover;
      display: block;
    }}
    .quality-media span {{
      position: absolute;
      left: 10px;
      bottom: 10px;
      padding: 5px 9px;
      border-radius: 999px;
      background: rgba(255,255,255,.9);
      color: #08784f;
      font-size: 12px;
      font-weight: 800;
    }}
    .quality-body, .tracker-card, .drill-card {{
      padding: 18px 20px 20px;
    }}
    .pose-grid {{
      display: grid;
      gap: 14px;
    }}
    .pose-media {{
      background: #dfe6dc;
    }}
    .pose-media img {{
      width: 100%;
      display: block;
      object-fit: cover;
      max-height: 680px;
    }}
    .pose-media.wide img {{
      max-height: none;
    }}
    .pose-body {{
      padding: 18px 20px 20px;
    }}
    .pose-body p {{
      margin: 0 0 12px;
      font-size: 17px;
      line-height: 1.42;
    }}
    .pose-lists {{
      display: grid;
      gap: 12px;
      margin-top: 14px;
    }}
    .pose-lists h4 {{
      margin: 0 0 7px;
      font-size: 17px;
      color: #08784f;
    }}
    .pose-lists ul {{
      margin: 0;
      padding-left: 20px;
      color: #415046;
      font-size: 16px;
      line-height: 1.4;
    }}
    .pose-lists li {{
      margin-bottom: 6px;
    }}
    .stroke-grid, .phase-detail-grid, .chain-grid, .evidence-grid {{
      display: grid;
      gap: 14px;
    }}
    .stroke-card, .chain-card, .evidence-card {{
      background: rgba(255,255,255,.88);
      border: 1px solid rgba(20,33,27,.08);
      box-shadow: 0 16px 42px rgba(20,33,27,.08);
      border-radius: 24px;
      overflow: hidden;
      padding: 18px 20px 20px;
    }}
    .stroke-head, .detail-top, .chain-top {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      margin-bottom: 10px;
    }}
    .stroke-head span, .detail-top b, .chain-top span, .evidence-body span {{
      flex: 0 0 auto;
      border-radius: 999px;
      padding: 5px 10px;
      background: #e4eee5;
      color: #08784f;
      font-size: 13px;
      font-weight: 800;
    }}
    .stroke-card > p, .chain-card > p {{
      margin: 0 0 14px;
      font-size: 17px;
      line-height: 1.42;
    }}
    .phase-detail, .chain-segment {{
      border-radius: 18px;
      background: #f4f1e8;
      overflow: hidden;
      border: 1px solid rgba(20,33,27,.08);
    }}
    .phase-thumb img {{
      width: 100%;
      display: block;
      max-height: 320px;
      object-fit: cover;
    }}
    .phase-detail-body, .chain-segment {{
      padding: 14px 15px;
    }}
    .phase-detail h4 {{
      margin: 0 0 8px;
      font-size: 20px;
      line-height: 1.15;
    }}
    .phase-detail p, .chain-segment p {{
      margin: 0 0 10px;
      font-size: 16px;
      line-height: 1.38;
    }}
    .chain-segment p b {{
      display: inline-block;
      min-width: 46px;
      color: #08784f;
      margin-right: 6px;
    }}
    .phase-detail.fix .detail-top b, .chain-segment.fix .chain-top span {{
      background: #ffe1df;
      color: #a33125;
    }}
    .phase-detail.watch .detail-top b, .chain-segment.watch .chain-top span {{
      background: #fff0c7;
      color: #8b5a00;
    }}
    .phase-detail.unknown .detail-top b, .chain-segment.unknown .chain-top span {{
      background: #e9ece8;
      color: #66736b;
    }}
    .evidence-card {{
      padding: 0;
      display: grid;
      grid-template-columns: 44% 1fr;
    }}
    .evidence-img {{
      min-height: 220px;
      background: #dfe6dc;
    }}
    .evidence-img img {{
      width: 100%;
      height: 100%;
      min-height: 220px;
      object-fit: cover;
      display: block;
    }}
    .evidence-body {{
      padding: 18px 20px 20px;
    }}
    .confidence-notes li {{
      color: #415046;
    }}
    .quality-body p, .tracker-card p, .drill-card p {{
      margin: 0 0 12px;
      font-size: 17px;
      line-height: 1.42;
    }}
    .metrics {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 8px;
    }}
    .metrics li {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      padding: 10px 12px;
      border-radius: 14px;
      background: #f4f1e8;
      font-size: 15px;
    }}
    .score {{
      flex: 0 0 auto;
      border-radius: 999px;
      padding: 4px 9px;
      background: #e4eee5;
      color: #08784f;
      font-weight: 800;
      font-size: 13px;
    }}
    .score.warn {{ background: #fff0c7; color: #8b5a00; }}
    .score.bad {{ background: #ffe1df; color: #a33125; }}
    .tracker-top {{
      display: grid;
      gap: 6px;
      margin-bottom: 10px;
    }}
    .tracker-top span {{
      width: fit-content;
      border-radius: 999px;
      padding: 5px 10px;
      background: #e4eee5;
      color: #08784f;
      font-size: 13px;
      font-weight: 800;
    }}
    .tracker-top strong {{
      font-size: 23px;
      line-height: 1.1;
    }}
    .tracker-card ul {{
      margin: 0 0 12px;
      padding-left: 20px;
      color: #415046;
      font-size: 16px;
      line-height: 1.38;
    }}
    .tracker-card li {{
      margin-bottom: 6px;
    }}
    .tracker-cue {{
      border-left: 4px solid #08784f;
      background: #edf5ee;
      color: #14211b;
      padding: 11px 12px;
      border-radius: 12px;
      font-weight: 800;
      line-height: 1.35;
    }}
    .tracker-card.watch .tracker-top span {{ background: #fff0c7; color: #8b5a00; }}
    .tracker-card.fix .tracker-top span {{ background: #ffe1df; color: #a33125; }}
    .tracker-card.good .tracker-top span {{ background: #e4eee5; color: #08784f; }}
    .drill-card ol {{
      margin: 0 0 12px;
      padding-left: 22px;
      font-size: 17px;
      line-height: 1.42;
    }}
    .drill-card li {{
      margin-bottom: 8px;
    }}
    @media (max-width: 620px) {{
      .page {{ padding: 14px 12px 32px; }}
      .hero {{ border-radius: 22px; min-height: 430px; }}
      .hero img {{ height: 500px; }}
      .meta {{ grid-template-columns: 1fr; }}
      .moment {{ grid-template-columns: 1fr; }}
      .moment-img, .moment-img img {{ min-height: 280px; }}
      .quality-media {{ grid-template-columns: 1fr 1fr; }}
      .quality-media div, .quality-media img {{ min-height: 220px; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      {image_tag(cover, data.get("title", ""))}
      <div class="hero-text">
        <div class="kicker">AI TENNIS COACH · {esc(today)}</div>
        <h1>{esc(data.get("title", "网球训练报告"))}</h1>
        <p class="one">{esc(data.get("one_liner", ""))}</p>
      </div>
    </section>

    <section class="meta">
      <div><b>本次重点</b>{esc(data.get("main_focus", ""))}</div>
      <div><b>场景</b>{esc(video.get("scene", ""))}</div>
      <div><b>置信度</b>{esc(confidence_label(data.get("confidence", "")))}</div>
    </section>

    <section class="section">
      <h2>教练小结</h2>
      <div class="card"><ul>{summary_html}</ul></div>
    </section>

    {render_capture_quality(capture_quality, analysis_dir, asset_dir)}

    {render_pose_analysis(pose_analysis, analysis_dir, asset_dir)}

    {render_stroke_analysis(stroke_analysis, analysis_dir, asset_dir)}

    {render_kinetic_chain(kinetic_chain)}

    {render_evidence_frames(evidence_frames, analysis_dir, asset_dir)}

    {render_confidence_notes(confidence_notes)}

    {render_problem_tracker(problem_tracker)}

    {render_phase_review(phase_review, analysis_dir, asset_dir)}

    <section class="section">
      <h2>值得夸的地方</h2>
      {render_cards(highlights, "highlight", analysis_dir, asset_dir)}
    </section>

    <section class="section">
      <h2>今天先改这里</h2>
      {render_cards(issues, "issue", analysis_dir, asset_dir)}
    </section>

    {render_training_prescription(training_prescription)}

    <section class="section">
      <h2>下一次怎么练</h2>
      <div class="practice"><ol>{practice_html}</ol></div>
      <p class="caption">{esc(data.get("social_caption", ""))}</p>
    </section>
  </main>
</body>
</html>"""


def first_text(values: list[object], fallback: str = "") -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def report_score(data: dict) -> int:
    if isinstance(data.get("score"), (int, float)):
        return max(0, min(100, int(round(float(data["score"])))))
    chain = data.get("kinetic_chain") or {}
    level = str(chain.get("overall_level") or "").lower()
    if level == "good":
        return 88
    if level == "fix":
        return 76
    if level == "unknown":
        return 72
    confidence = str(data.get("confidence") or "").lower()
    if confidence == "high":
        return 86
    if confidence == "low":
        return 74
    return 80


def stage_label(score: int) -> str:
    if score >= 90:
        return "高阶稳定阶段（Advanced+）"
    if score >= 80:
        return "高级进阶阶段（Advanced）"
    if score >= 70:
        return "进阶建立阶段（Intermediate）"
    return "基础修正阶段（Foundation）"


def report_metrics(data: dict) -> list[tuple[str, int]]:
    explicit = data.get("ability_radar")
    if isinstance(explicit, list) and explicit:
        rows = []
        for row in explicit:
            if isinstance(row, dict):
                label = str(row.get("label") or row.get("name") or "")
                value = row.get("value", 0)
                if label:
                    rows.append((label, max(0, min(100, int(float(value))))))
        if rows:
            return rows[:6]

    base = {
        "准备启动": 80,
        "动力链": 78,
        "击球时机": 79,
        "随挥收拍": 82,
        "拍面控制": 80,
        "身体稳定": 79,
    }
    chain = data.get("kinetic_chain") or {}
    for segment in chain.get("segments", []):
        label = str(segment.get("label") or "")
        level = str(segment.get("level") or "").lower()
        value = {"good": 86, "watch": 80, "fix": 72, "unknown": 66}.get(level)
        if value is None:
            continue
        if "脚" in label or "距离" in label:
            base["准备启动"] = value
        elif "腿" in label or "髋" in label:
            base["动力链"] = value
        elif "肩" in label or "躯干" in label:
            base["身体稳定"] = value
        elif "拍" in label or "触球" in label:
            base["击球时机"] = value
    return list(base.items())


def radar_svg(metrics: list[tuple[str, int]]) -> str:
    size = 280
    cx = cy = size / 2
    radius = 92
    count = len(metrics)
    if count < 3:
        return ""

    def point(index: int, value: float) -> tuple[float, float]:
        angle = -math.pi / 2 + index * (2 * math.pi / count)
        r = radius * value
        return cx + math.cos(angle) * r, cy + math.sin(angle) * r

    rings = []
    for scale in (0.2, 0.4, 0.6, 0.8, 1.0):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, scale) for i in range(count)))
        rings.append(f'<polygon points="{pts}" fill="none" stroke="rgba(45,151,255,.22)" stroke-width="2"/>')
    axes = []
    labels = []
    for i, (label, _) in enumerate(metrics):
        x, y = point(i, 1.0)
        axes.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="rgba(45,151,255,.18)" stroke-width="2"/>')
        lx, ly = point(i, 1.24)
        labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle">{esc(label)}</text>')
    data_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, value / 100) for i, (_, value) in enumerate(metrics)))
    return f"""
      <svg class="radar" viewBox="0 0 {size} {size}" role="img" aria-label="能力雷达">
        {''.join(rings)}
        {''.join(axes)}
        <polygon points="{data_pts}" fill="rgba(20,145,255,.62)" stroke="#1da1ff" stroke-width="4"/>
        <circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#35aaff"/>
        {''.join(labels)}
      </svg>
    """


def render_metric_bars(metrics: list[tuple[str, int]]) -> str:
    rows = []
    for label, value in metrics:
        rows.append(f"""
          <div class="metric-row">
            <span>{esc(label)}</span>
            <div class="metric-track"><i style="width:{value}%"></i></div>
            <b>{value}</b>
          </div>
        """)
    return "".join(rows)


def focus_blocks(data: dict) -> list[tuple[str, str, str, str]]:
    highlights = data.get("highlights") or []
    issues = data.get("issues") or []
    next_practice = data.get("next_practice") or []
    good = first_text([highlights[0].get("note") if highlights else ""], "准备与启动机制积极，能在来球后保持主动调整。")
    issue = first_text([issues[0].get("impact") if issues else "", issues[0].get("evidence") if issues else ""], "动力链底端的稳定支撑还不足，面对更快来球时容易让击球点不稳定。")
    next_step = first_text(next_practice, "下一次训练先抓准备启动和击球后回位，再逐步提高来球强度。")
    return [
        ("亮点", "good", "准备与启动机制积极", good),
        ("待改进", "warn", "动力链底端支撑仍不足", issue),
        ("下一步", "info", "下肢爆发与安全制动", next_step),
    ]


def render_focus_blocks(data: dict) -> str:
    cards = []
    for label, kind, title, body in focus_blocks(data):
        cards.append(f"""
          <article class="focus-item {kind}">
            <div class="focus-icon"></div>
            <div>
              <h3>{esc(label)}</h3>
              <h4>{esc(title)}</h4>
              <p>{esc(body)}</p>
            </div>
          </article>
        """)
    return "".join(cards)


def render_key_moments_dark(data: dict) -> str:
    rows = []
    phases = data.get("phase_review") or data.get("phase_reviews") or []
    evidence = data.get("evidence_frames") or []
    source = phases[:2] if phases else evidence[:2]
    for item in source:
        timestamp = str(item.get("timestamp") or "")
        title = str(item.get("label") or item.get("title") or item.get("phase") or "关键片段")
        headline = str(item.get("change") or item.get("claim") or item.get("issue") or item.get("note") or "")
        detail = str(item.get("issue") or item.get("cue") or item.get("confidence") or "")
        rows.append(f"""
          <article class="moment-dark">
            <div class="time-badge"><b>{esc(timestamp)}</b><span>{esc(item.get("clip_end", ""))}</span></div>
            <div>
              <h3>{esc(title)}</h3>
              <h4>{esc(headline)}</h4>
              <p>{esc(detail)}</p>
            </div>
          </article>
        """)
    if not rows:
        rows.append("""
          <article class="moment-dark">
            <div class="time-badge"><b>--</b><span></span></div>
            <div><h3>关键片段</h3><h4>请在分析中补充具体时间点</h4><p>报告会把每个判断绑定到证据画面。</p></div>
          </article>
        """)
    return "".join(rows)


def render_insights_dark(data: dict) -> str:
    chain = data.get("kinetic_chain") or {}
    issues = data.get("issues") or []
    stroke = data.get("stroke_analysis") or []
    items = [
        ("打球风格", first_text([data.get("main_focus"), data.get("one_liner")], "节奏型、稳定型打法")),
        ("球路组织", first_text([stroke[0].get("summary") if stroke else "", chain.get("summary")], "依赖连续调整寻找对抗机会。")),
        ("负荷风险", first_text([issues[0].get("impact") if issues else ""], "强度上升时，如果准备和制动不足，容易让手臂承担过多补救压力。")),
    ]
    return "".join(f"""
      <article class="insight-card">
        <div class="insight-icon"></div>
        <div>
          <h3>{esc(title)}</h3>
          <p>{esc(body)}</p>
        </div>
      </article>
    """ for title, body in items)


def render_html(data: dict, analysis_path: Path, outdir: Path) -> str:
    analysis_dir = analysis_path.parent
    asset_dir = outdir / "assets"
    cover = rel_asset(data.get("cover_frame"), analysis_dir, asset_dir)
    if not cover:
        highlights = data.get("highlights") or []
        cover = rel_asset(highlights[0].get("frame") if highlights else None, analysis_dir, asset_dir)
    video = data.get("video") or {}
    today = data.get("date") or date.today().isoformat()
    score = report_score(data)
    metrics = report_metrics(data)
    summaries = data.get("coach_summary") or []
    summary = first_text(summaries, data.get("one_liner", "动作节奏和动力链报告已生成。"))
    headline = first_text([data.get("headline"), data.get("main_focus")], "动作节奏清晰，具备继续提升的基础")
    ntrp = data.get("ntrp") or "约 NTRP 3.2"
    confidence = data.get("analysis_confidence") or f"分析置信度 {confidence_label(data.get('confidence', 'medium'))}"
    stage = stage_label(score)
    main_body = " ".join(str(s) for s in summaries[1:3]) or str(data.get("one_liner") or "")
    if not main_body:
        main_body = "本报告会把关键判断绑定到具体时间点、画面和慢动作片段，优先指出最值得修正的一处动作链断点。"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(data.get("title", "AI 综合分析报告"))}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: #0c101c;
      color: #eef3ff;
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", Arial, sans-serif;
    }}
    .page {{
      width: min(100%, 900px);
      margin: 0 auto;
      padding: 64px 26px 44px;
      background:
        radial-gradient(circle at 50% 0%, rgba(46, 82, 150, .18), transparent 34%),
        linear-gradient(180deg, #0b0f1b 0%, #151929 52%, #0d1220 100%);
    }}
    .panel {{
      position: relative;
      overflow: hidden;
      border-radius: 20px;
      background: linear-gradient(180deg, rgba(39,44,61,.96), rgba(32,37,54,.96));
      border: 1px solid rgba(255,255,255,.08);
      box-shadow: 0 18px 40px rgba(0,0,0,.34), inset 0 1px 0 rgba(255,255,255,.05);
      margin-bottom: 24px;
    }}
    .analysis-card {{
      padding: 28px 28px 30px;
      text-align: center;
    }}
    .eyebrow {{
      margin: 0 0 18px;
      color: #aeb7c9;
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .score-line {{
      display: inline-flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 12px;
    }}
    .score-line strong {{
      font-size: 78px;
      line-height: .86;
      font-weight: 900;
      letter-spacing: 0;
      color: #ffffff;
    }}
    .score-line span {{
      font-size: 26px;
      color: #d7ddea;
      font-weight: 800;
    }}
    .stage {{
      margin: 0 auto 18px;
      max-width: 690px;
      color: #4ee074;
      font-size: 21px;
      line-height: 1.45;
      font-weight: 800;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 24px;
      border-radius: 999px;
      background: linear-gradient(90deg, #ff9c22, #ff6f23);
      color: white;
      font-weight: 900;
      font-size: 18px;
      margin: 0 0 20px;
      box-shadow: 0 12px 24px rgba(255, 117, 30, .28);
    }}
    .chips {{
      display: flex;
      justify-content: center;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 20px;
    }}
    .chip {{
      padding: 8px 15px;
      border-radius: 999px;
      background: rgba(255,255,255,.1);
      color: #e6ecf8;
      font-size: 15px;
      font-weight: 800;
    }}
    .chip.primary {{
      background: rgba(0,145,255,.18);
      color: #2da4ff;
    }}
    h1, h2, h3, h4, p {{ letter-spacing: 0; }}
    .analysis-card h1 {{
      margin: 0 0 14px;
      font-size: 27px;
      line-height: 1.22;
      color: #fff;
    }}
    .analysis-card p {{
      margin: 0;
      color: #d3d9e8;
      font-size: 19px;
      line-height: 1.62;
    }}
    .replay {{
      height: 360px;
      padding: 18px;
    }}
    .replay-bg {{
      position: absolute;
      inset: 0;
      background-image: url("{esc(cover)}");
      background-size: cover;
      background-position: center;
      filter: blur(18px) brightness(.7);
      transform: scale(1.08);
      opacity: .75;
    }}
    .replay img {{
      position: relative;
      z-index: 2;
      width: 78%;
      height: 100%;
      margin: 0 auto;
      display: block;
      object-fit: cover;
      border-radius: 14px;
      box-shadow: 0 14px 38px rgba(0,0,0,.32);
    }}
    .replay-label {{
      position: absolute;
      z-index: 3;
      top: 28px;
      left: 110px;
      padding: 8px 13px;
      border-radius: 999px;
      background: rgba(22, 27, 41, .74);
      color: white;
      font-size: 13px;
      font-weight: 900;
    }}
    .section-title {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 0 0 18px;
      color: #f3f6ff;
      font-size: 23px;
      line-height: 1.2;
    }}
    .section-title i {{
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: #168cff;
      box-shadow: 0 0 16px rgba(22,140,255,.8);
    }}
    .section-body {{ padding: 24px; }}
    .focus-list, .moment-list, .insight-list {{
      display: grid;
      gap: 14px;
    }}
    .focus-item, .moment-dark, .insight-card {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 15px;
      padding: 18px;
      border-radius: 16px;
      background: rgba(20, 25, 39, .72);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
    }}
    .focus-icon, .insight-icon {{
      width: 34px;
      height: 34px;
      border-radius: 50%;
      margin-top: 2px;
      background: #168cff;
      box-shadow: 0 0 18px rgba(22,140,255,.45);
    }}
    .focus-item.good .focus-icon {{ background: #24d86c; }}
    .focus-item.warn .focus-icon {{ background: #ffad22; }}
    .focus-item.info .focus-icon {{ background: #168cff; }}
    .insight-card:nth-child(1) .insight-icon {{ background: #9b4dff; }}
    .insight-card:nth-child(2) .insight-icon {{ background: #18a8c9; }}
    .insight-card:nth-child(3) .insight-icon {{ background: #ff3f4f; }}
    .focus-item h3, .focus-item h4, .insight-card h3, .moment-dark h3, .moment-dark h4 {{
      margin: 0;
    }}
    .focus-item h3 {{
      color: #fff;
      font-size: 20px;
      margin-bottom: 5px;
    }}
    .focus-item h4, .moment-dark h4 {{
      color: #eef3ff;
      font-size: 17px;
      line-height: 1.35;
      margin-bottom: 7px;
    }}
    .focus-item p, .moment-dark p, .insight-card p {{
      margin: 0;
      color: #c9d1e1;
      font-size: 16px;
      line-height: 1.58;
    }}
    .radar-wrap {{
      display: grid;
      justify-items: center;
      gap: 10px;
    }}
    .radar {{
      width: min(100%, 430px);
      height: auto;
      margin: 0 auto 6px;
    }}
    .radar text {{
      fill: #dce6f8;
      font-size: 14px;
      font-weight: 800;
    }}
    .metric-list {{
      width: 100%;
      display: grid;
      gap: 10px;
      margin-top: 6px;
    }}
    .metric-row {{
      display: grid;
      grid-template-columns: 96px 1fr 38px;
      gap: 10px;
      align-items: center;
      color: #dce4f3;
      font-size: 15px;
      font-weight: 800;
    }}
    .metric-track {{
      height: 10px;
      border-radius: 999px;
      background: rgba(255,255,255,.12);
      overflow: hidden;
    }}
    .metric-track i {{
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #147cff, #20a8ff);
    }}
    .metric-row b {{
      color: #1da1ff;
      font-size: 14px;
      text-align: right;
    }}
    .time-badge {{
      width: 58px;
      min-height: 48px;
      border-radius: 14px;
      background: rgba(12, 74, 116, .62);
      color: #ccefff;
      display: grid;
      place-items: center;
      align-content: center;
      font-size: 13px;
      font-weight: 900;
    }}
    .time-badge span {{
      display: block;
      color: #91b7d6;
      font-weight: 800;
      margin-top: 2px;
    }}
    .insight-card h3, .moment-dark h3 {{
      color: #ffffff;
      font-size: 20px;
      margin-bottom: 7px;
    }}
    .footer {{
      color: #7f8ca5;
      text-align: center;
      font-size: 16px;
      padding: 8px 0 0;
    }}
    @media (max-width: 620px) {{
      .page {{ padding: 34px 13px 28px; }}
      .analysis-card {{ padding: 24px 18px 24px; }}
      .score-line strong {{ font-size: 58px; }}
      .score-line span {{ font-size: 20px; }}
      .stage {{ font-size: 17px; }}
      .badge {{ font-size: 15px; padding: 9px 18px; }}
      .analysis-card h1 {{ font-size: 21px; }}
      .analysis-card p {{ font-size: 15px; line-height: 1.55; }}
      .replay {{ height: 180px; padding: 12px; }}
      .replay img {{ width: 76%; border-radius: 10px; }}
      .replay-label {{ left: 58px; top: 20px; font-size: 11px; }}
      .section-body {{ padding: 18px 14px; }}
      .section-title {{ font-size: 18px; }}
      .focus-item, .moment-dark, .insight-card {{ padding: 14px; gap: 11px; }}
      .focus-item p, .moment-dark p, .insight-card p {{ font-size: 13px; }}
      .focus-item h3, .insight-card h3, .moment-dark h3 {{ font-size: 16px; }}
      .focus-item h4, .moment-dark h4 {{ font-size: 14px; }}
      .metric-row {{ grid-template-columns: 72px 1fr 28px; font-size: 12px; }}
      .time-badge {{ width: 49px; font-size: 11px; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="panel analysis-card">
      <p class="eyebrow">AI 综合分析报告</p>
      <div class="score-line"><strong>{score}</strong><span>/100</span></div>
      <p class="stage">已进入{esc(stage)}，{esc(summary)}</p>
      <div class="badge">掌控全场的节奏舞者</div>
      <div class="chips">
        <span class="chip primary">进阶</span>
        <span class="chip">{esc(ntrp)}</span>
        <span class="chip">{esc(confidence)}</span>
      </div>
      <h1>{esc(headline)}</h1>
      <p>{esc(main_body)}</p>
    </section>

    <section class="panel replay">
      <div class="replay-bg"></div>
      <div class="replay-label">本场回顾</div>
      {image_tag(cover, "本场回顾")}
    </section>

    <section class="panel">
      <div class="section-body">
        <h2 class="section-title"><i></i>本次诊断重点</h2>
        <div class="focus-list">{render_focus_blocks(data)}</div>
      </div>
    </section>

    <section class="panel">
      <div class="section-body">
        <h2 class="section-title"><i></i>能力雷达</h2>
        <div class="radar-wrap">
          {radar_svg(metrics)}
          <div class="metric-list">{render_metric_bars(metrics)}</div>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="section-body">
        <h2 class="section-title"><i></i>关键时刻</h2>
        <div class="moment-list">{render_key_moments_dark(data)}</div>
      </div>
    </section>

    <section class="panel">
      <div class="section-body">
        <h2 class="section-title"><i></i>进阶洞察</h2>
        <div class="insight-list">{render_insights_dark(data)}</div>
      </div>
    </section>

    <footer class="footer">小球圈 · AI 综合分析</footer>
  </main>
</body>
</html>"""


def export_with_playwright(html_path: Path, outdir: Path, do_pdf: bool, do_png: bool) -> list[str]:
    exported: list[str] = []
    if not (do_pdf or do_png):
        return exported
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed; skipped PDF/PNG export.", file=sys.stderr)
        return exported

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        if do_pdf:
            page = browser.new_page(viewport={"width": 860, "height": 1200}, device_scale_factor=1)
            page.goto(html_path.as_uri(), wait_until="networkidle")
            pdf_path = outdir / "tennis-report.pdf"
            page.pdf(path=str(pdf_path), format="A4", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            exported.append(str(pdf_path))
        if do_png:
            page = browser.new_page(viewport={"width": 430, "height": 932}, device_scale_factor=2)
            page.goto(html_path.as_uri(), wait_until="networkidle")
            png_path = outdir / "tennis-report-mobile.png"
            page.screenshot(path=str(png_path), full_page=True)
            exported.append(str(png_path))
        browser.close()
    return exported


def main() -> int:
    parser = argparse.ArgumentParser(description="Render tennis coaching report from analysis.json.")
    parser.add_argument("analysis_json", type=Path)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args()

    analysis_path = args.analysis_json.expanduser().resolve()
    if not analysis_path.exists():
        raise SystemExit(f"analysis.json not found: {analysis_path}")
    outdir = args.outdir.expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    data = json.loads(analysis_path.read_text(encoding="utf-8"))
    html_text = render_html(data, analysis_path, outdir)
    html_path = outdir / "index.html"
    html_path.write_text(html_text, encoding="utf-8")
    exported = export_with_playwright(html_path, outdir, args.pdf, args.png)
    print(json.dumps({"html": str(html_path), "exported": exported}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

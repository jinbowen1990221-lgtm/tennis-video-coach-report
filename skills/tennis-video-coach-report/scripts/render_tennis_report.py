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


def score_value(value: object) -> int | None:
    if isinstance(value, (int, float)):
        return max(0, min(100, int(round(float(value)))))
    if isinstance(value, str) and value.strip():
        try:
            return max(0, min(100, int(round(float(value)))))
        except ValueError:
            return None
    return None


def scoring_items(data: dict) -> list[dict]:
    scoring = data.get("scoring") or data.get("movement_scoring") or {}
    if isinstance(scoring, dict):
        for key in ("items", "metrics", "breakdown"):
            items = scoring.get(key)
            if isinstance(items, list) and items:
                return [item for item in items if isinstance(item, dict)]
    for key in ("movement_scores", "score_breakdown", "ability_radar"):
        items = data.get(key)
        if isinstance(items, list) and items:
            return [item for item in items if isinstance(item, dict)]
    return []


def report_score(data: dict) -> int:
    scoring = data.get("scoring") or data.get("movement_scoring") or {}
    if isinstance(scoring, dict):
        explicit = score_value(scoring.get("overall") or scoring.get("score") or scoring.get("action_score"))
        if explicit is not None:
            return explicit
    if isinstance(data.get("score"), (int, float)):
        return max(0, min(100, int(round(float(data["score"])))))
    action = data.get("action_score") or data.get("movement_score")
    explicit_action = score_value(action)
    if explicit_action is not None:
        return explicit_action
    metric_values = [value for _, value in report_metrics(data) if value > 0]
    if metric_values:
        return int(round(sum(metric_values) / len(metric_values)))
    chain = data.get("kinetic_chain") or {}
    level = str(chain.get("overall_level") or "").lower()
    if level == "good":
        return 88
    if level == "fix":
        return 76
    if level == "unknown":
        return 72
    return 0


def stage_label(score: int) -> str:
    if score >= 90:
        return "动作链高效阶段（Advanced+）"
    if score >= 80:
        return "动力链进阶阶段（Advanced）"
    if score >= 70:
        return "动作连接建立阶段（Intermediate）"
    return "基础动作重建阶段（Foundation）"


def report_metrics(data: dict) -> list[tuple[str, int]]:
    explicit = scoring_items(data)
    if explicit:
        rows = []
        for row in explicit:
            label = str(row.get("label") or row.get("name") or row.get("metric") or "")
            value = score_value(row.get("value") or row.get("score"))
            if label and value is not None:
                rows.append((label, value))
        if rows:
            return rows[:6]

    base = dict.fromkeys(["准备启动", "动力链", "击球时机", "挥速释放", "随挥收拍", "身体稳定"], 0)
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
    speed = data.get("swing_speed") or {}
    if isinstance(speed, dict):
        value = speed.get("score") or speed.get("release_score")
        speed_value = score_value(value)
        if speed_value is not None:
            base["挥速释放"] = speed_value
    return [(label, value) for label, value in base.items() if value > 0]


def scoring_note(data: dict) -> str:
    scoring = data.get("scoring") or data.get("movement_scoring") or {}
    if isinstance(scoring, dict):
        note = first_text([scoring.get("summary"), scoring.get("method_note"), scoring.get("evidence_note")])
        if note:
            return note
    readable = len(data.get("evidence_frames") or []) + len(data.get("phase_review") or data.get("phase_reviews") or [])
    if readable:
        return f"分数基于视频中 {readable} 组可读动作片段、关键帧和慢动作观察生成。"
    return "分数仅在视频动作证据可读时生成；证据不足的项目不应强行评分。"


ICON_ASSET_FILES = {
    "check": "亮点.svg",
    "warn": "待改进.svg",
    "next": "下一步.svg",
    "insight": "风格.svg",
    "route": "球路组织.svg",
    "load": "风险.svg",
}


def asset_icon_svg(name: str) -> str:
    icon_file = ICON_ASSET_FILES.get(name)
    if not icon_file:
        return ""
    path = Path(__file__).resolve().parent.parent / "assets" / "icons" / icon_file
    if not path.exists():
        return ""
    svg = path.read_text(encoding="utf-8").strip()
    start = svg.find("<svg")
    if start >= 0:
        svg = svg[start:]
    svg = svg.replace("<svg ", '<svg class="asset-icon" aria-hidden="true" ', 1)
    for color in ("#333", "#333333", "black"):
        svg = svg.replace(f'stroke="{color}"', 'stroke="currentColor"')
        svg = svg.replace(f"stroke='{color}'", 'stroke="currentColor"')
        svg = svg.replace(f'fill="{color}"', 'fill="currentColor"')
        svg = svg.replace(f"fill='{color}'", 'fill="currentColor"')
    return svg


def icon_svg(name: str) -> str:
    asset_svg = asset_icon_svg(name)
    if asset_svg:
        return asset_svg
    icons = {
        "target": '<path d="M12 3a9 9 0 1 0 9 9h-3a6 6 0 1 1-6-6V3Z"/><path d="M12 8a4 4 0 1 0 4 4h-3a1 1 0 1 1-1-1V8Z"/><path d="M13 3h8v3h-5v5h-3V3Z"/>',
        "check": '<path d="M20 6 9 17l-5-5"/><path d="M21 12a9 9 0 1 1-5.3-8.2"/>',
        "warn": '<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5"/><path d="M12 18h.01"/>',
        "next": '<path d="M5 12h12"/><path d="m13 6 6 6-6 6"/><path d="M5 5v14"/>',
        "radar": '<path d="M12 2 21 7v10l-9 5-9-5V7l9-5Z"/><path d="M12 6 17 9v6l-5 3-5-3V9l5-3Z"/><path d="M12 2v20"/><path d="M3 7l18 10"/><path d="M21 7 3 17"/>',
        "clock": '<path d="M12 8v5l3 2"/><path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>',
        "insight": '<path d="M9 18h6"/><path d="M10 22h4"/><path d="M8.6 15.2a6 6 0 1 1 6.8 0c-.8.5-1.4 1.4-1.4 2.3h-4c0-.9-.6-1.8-1.4-2.3Z"/>',
        "route": '<path d="M6 18a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M18 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M6 12V8a2 2 0 0 1 2-2h7"/><path d="M9 15h7a2 2 0 0 0 2-2v-1"/>',
        "load": '<path d="M12 2v5"/><path d="M12 17v5"/><path d="M4.9 4.9 8.4 8.4"/><path d="m15.6 15.6 3.5 3.5"/><path d="M2 12h5"/><path d="M17 12h5"/><path d="m4.9 19.1 3.5-3.5"/><path d="m15.6 8.4 3.5-3.5"/><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/>',
        "speed": '<path d="M4 17a8 8 0 1 1 16 0"/><path d="M12 17l4-7"/><path d="M8 17h8"/>',
        "chain": '<path d="M7 7h.01"/><path d="M17 7h.01"/><path d="M7 17h.01"/><path d="M17 17h.01"/><path d="M7 7h10v10H7z"/>',
    }
    path = icons.get(name, icons["target"])
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{path}</svg>'


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
    icon_names = {"good": "check", "warn": "warn", "info": "next"}
    for label, kind, title, body in focus_blocks(data):
        cards.append(f"""
          <article class="focus-item {kind}">
            <div class="icon-shell">{icon_svg(icon_names.get(kind, "target"))}</div>
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
    icons = ["insight", "route", "load"]
    return "".join(f"""
      <article class="insight-card">
        <div class="icon-shell">{icon_svg(icons[index])}</div>
        <div>
          <h3>{esc(title)}</h3>
          <p>{esc(body)}</p>
        </div>
      </article>
    """ for index, (title, body) in enumerate(items))


def selected_issue_phase(data: dict) -> dict:
    phases = data.get("phase_review") or data.get("phase_reviews") or []
    for phase in phases:
        if phase.get("issue") or phase.get("annotated_slow_clip"):
            return phase
    return phases[0] if phases else {}


def chain_steps(data: dict) -> list[tuple[str, str, str]]:
    chain = data.get("kinetic_chain") or {}
    segments = chain.get("segments") or []
    rows = []
    for segment in segments[:4]:
        label = str(segment.get("label") or segment.get("segment") or "")
        level = str(segment.get("level") or "watch")
        cue = str(segment.get("cue") or segment.get("evidence") or "")
        if label:
            rows.append((label, level, cue))
    if rows:
        return rows
    return [
        ("脚步到位", "watch", "先到球旁边"),
        ("髋躯干传导", "fix", "转体完成偏晚"),
        ("手臂释放", "watch", "避免最后一刻补救"),
        ("拍头加速", "unknown", "远机位需谨慎判断"),
    ]


def render_chain_steps(data: dict) -> str:
    rows = []
    for index, (label, level, cue) in enumerate(chain_steps(data), start=1):
        rows.append(f"""
          <div class="chain-step {esc(level)}">
            <b>{index}</b>
            <span>{esc(label)}</span>
            <small>{esc(cue)}</small>
          </div>
        """)
    return "".join(rows)


def top_review_media(data: dict, analysis_dir: Path, asset_dir: Path) -> tuple[str, str, dict]:
    phase = selected_issue_phase(data)
    video = rel_media(
        data.get("top_review_clip")
        or phase.get("normal_clip")
        or phase.get("clean_clip")
        or phase.get("raw_clip")
        or phase.get("annotated_slow_clip")
        or phase.get("clip"),
        analysis_dir,
        asset_dir,
    )
    poster = rel_asset(
        data.get("top_review_poster")
        or phase.get("frame")
        or data.get("cover_frame")
        or phase.get("freeze_frame"),
        analysis_dir,
        asset_dir,
    )
    return video, poster, phase


def swing_speed_model(data: dict) -> dict:
    explicit = data.get("swing_speed")
    if isinstance(explicit, dict) and explicit:
        return explicit
    metrics = dict(report_metrics(data))
    speed_score = int(metrics.get("挥速释放", 0))
    if speed_score <= 0:
        return {
            "score": 0,
            "level": "视频证据不足",
            "summary": "当前视频或分析数据不足以单独判断挥速释放，不应强行给出挥速分。",
            "items": [
                {"label": "启动加速", "value": 0, "note": "需要可读的准备到触球完整片段。"},
                {"label": "峰值释放", "value": 0, "note": "需要能看到拍头进入击球区的慢动作。"},
                {"label": "减速收拍", "value": 0, "note": "需要能看到击球后随挥和回位。"},
            ],
        }
    return {
        "score": speed_score,
        "level": "中等偏稳",
        "summary": "挥速不是主要瓶颈，当前更受准备时机和动力链传导影响。脚步和转体提前后，拍头速度会更自然释放。",
        "items": [
            {"label": "启动加速", "value": max(0, min(100, speed_score - 4)), "note": "来球早期准备偏晚，压缩了加速距离。"},
            {"label": "峰值释放", "value": speed_score, "note": "击球前仍有释放空间，但需要身体先带动。"},
            {"label": "减速收拍", "value": max(0, min(100, speed_score + 5)), "note": "随挥能完成，打完回位还可更快。"},
        ],
    }


def render_swing_speed(data: dict) -> str:
    speed = swing_speed_model(data)
    score = max(0, min(100, int(float(speed.get("score", 0)))))
    rows = []
    for item in speed.get("items", []):
        value = max(0, min(100, int(float(item.get("value", 0)))))
        rows.append(f"""
          <div class="speed-row">
            <div>
              <strong>{esc(item.get("label", ""))}</strong>
              <p>{esc(item.get("note", ""))}</p>
            </div>
            <div class="speed-meter"><i style="width:{value}%"></i></div>
            <b>{value}</b>
          </div>
        """)
    return f"""
      <section class="panel">
        <div class="section-body">
          <h2 class="section-title"><span class="title-icon">{icon_svg("speed")}</span>挥速分析</h2>
          <div class="speed-hero">
            <div class="speed-score"><strong>{score}</strong><span>/100</span></div>
            <div>
              <h3>{esc(speed.get("level", "挥速评估"))}</h3>
              <p>{esc(speed.get("summary", ""))}</p>
            </div>
          </div>
          <div class="speed-list">{''.join(rows)}</div>
        </div>
      </section>
    """


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
    review_video, review_poster, review_phase = top_review_media(data, analysis_dir, asset_dir)
    summaries = data.get("coach_summary") or []
    summary = first_text(summaries, data.get("one_liner", "动作节奏和动力链报告已生成。"))
    headline = first_text([data.get("headline"), data.get("main_focus")], "动力链连接清晰度具备提升空间")
    ntrp = data.get("ntrp") or "约 NTRP 3.2"
    confidence = data.get("analysis_confidence") or f"分析置信度 {confidence_label(data.get('confidence', 'medium'))}"
    stage = stage_label(score)
    review_title = first_text([data.get("top_review_title"), review_phase.get("label"), "针对性问题片段"], "针对性问题片段")
    review_issue = first_text(
        [data.get("top_review_note"), review_phase.get("issue"), review_phase.get("change")],
        "截取最能体现动作链断点的一小段，叠加脚步、转体、手臂释放和拍头加速的动力链标注。",
    )
    score_note = scoring_note(data)
    main_body = " ".join(str(s) for s in summaries[1:3]) or str(data.get("one_liner") or "")
    if not main_body:
        main_body = "本报告会把关键判断绑定到具体时间点、画面和慢动作片段，优先指出最值得修正的一处动作链断点。"
    if review_video:
        poster_attr = f' poster="{esc(review_poster)}"' if review_poster else ""
        review_media_html = f'<video controls playsinline preload="metadata"{poster_attr}><source src="{esc(review_video)}" type="video/mp4"></video>'
    else:
        review_media_html = image_tag(review_poster or cover, "针对性问题片段")
    score_angle = max(0, min(360, int(round(score * 3.6))))

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
      padding: 18px;
    }}
    .replay-bg {{
      position: absolute;
      inset: 0;
      background-image: url("{esc(review_poster or cover)}");
      background-size: cover;
      background-position: center;
      filter: blur(18px) brightness(.7);
      transform: scale(1.08);
      opacity: .75;
    }}
    .review-shell {{
      position: relative;
      z-index: 2;
      width: 82%;
      margin: 0 auto;
    }}
    .review-shell img, .review-shell video {{
      width: 100%;
      aspect-ratio: 16 / 9;
      display: block;
      object-fit: cover;
      border-radius: 14px;
      box-shadow: 0 14px 38px rgba(0,0,0,.32);
      background: #101626;
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
    .review-note {{
      position: relative;
      z-index: 2;
      width: 82%;
      margin: 12px auto 0;
      padding: 11px 14px;
      border-radius: 14px;
      background: rgba(16, 22, 37, .74);
      color: #dfe8f7;
      font-size: 15px;
      line-height: 1.5;
      font-weight: 750;
    }}
    .chain-overlay {{
      position: relative;
      z-index: 2;
      width: 82%;
      margin: 12px auto 0;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
    }}
    .chain-step {{
      min-height: 78px;
      padding: 10px;
      border-radius: 13px;
      background: rgba(14, 20, 34, .78);
      border: 1px solid rgba(255,255,255,.08);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
    }}
    .chain-step b {{
      display: inline-grid;
      place-items: center;
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: #2196ff;
      color: #fff;
      font-size: 12px;
      margin-bottom: 7px;
    }}
    .chain-step.good b {{ background: #24d86c; }}
    .chain-step.watch b, .chain-step.warn b {{ background: #ffad22; }}
    .chain-step.fix b {{ background: #ff3f4f; }}
    .chain-step span {{
      display: block;
      color: #fff;
      font-size: 13px;
      font-weight: 900;
      line-height: 1.25;
      margin-bottom: 4px;
    }}
    .chain-step small {{
      display: block;
      color: #b9c4d6;
      font-size: 11px;
      line-height: 1.35;
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
    .title-icon {{
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: #168cff;
      box-shadow: 0 0 16px rgba(22,140,255,.8);
      display: inline-grid;
      place-items: center;
      flex: 0 0 auto;
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
    .icon-shell {{
      width: 34px;
      height: 34px;
      border-radius: 50%;
      margin-top: 2px;
      background: #168cff;
      box-shadow: 0 0 18px rgba(22,140,255,.45);
      display: inline-grid;
      place-items: center;
    }}
    .title-icon svg, .icon-shell svg, .badge svg {{
      width: 18px;
      height: 18px;
      stroke: #fff;
      fill: none;
      stroke-width: 2.4;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .title-icon svg {{ width: 14px; height: 14px; }}
    .badge svg {{ width: 20px; height: 20px; }}
    .icon-shell svg [fill]:not([fill="none"]) {{ fill: #fff; }}
    .icon-shell svg [stroke] {{ stroke: #fff; }}
    .focus-item.good .icon-shell {{ background: #24d86c; }}
    .focus-item.warn .icon-shell {{ background: #ffad22; }}
    .focus-item.info .icon-shell {{ background: #168cff; }}
    .insight-card:nth-child(1) .icon-shell {{ background: #9b4dff; }}
    .insight-card:nth-child(2) .icon-shell {{ background: #18a8c9; }}
    .insight-card:nth-child(3) .icon-shell {{ background: #ff3f4f; }}
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
    .score-note {{
      width: 100%;
      margin: 10px 0 0;
      padding: 10px 12px;
      border-radius: 12px;
      background: rgba(20, 25, 39, .62);
      color: #aeb9cc;
      font-size: 13px;
      line-height: 1.45;
      text-align: left;
    }}
    .speed-hero {{
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 16px;
      align-items: center;
      justify-items: center;
      padding: 18px;
      border-radius: 16px;
      background: rgba(20, 25, 39, .72);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
      margin-bottom: 14px;
      text-align: center;
    }}
    .speed-score {{
      width: 94px;
      height: 94px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      align-content: center;
      background:
        radial-gradient(circle at 50% 50%, #24334d 0 52%, transparent 53%),
        conic-gradient(#20a8ff 0deg, #147cff 276deg, rgba(255,255,255,.12) 276deg 360deg);
      box-shadow: 0 12px 28px rgba(20, 124, 255, .22);
    }}
    .speed-score strong {{
      display: block;
      font-size: 28px;
      line-height: 1;
      color: #fff;
    }}
    .speed-score span {{
      color: #aeb9cc;
      font-size: 12px;
      font-weight: 900;
    }}
    .speed-hero h3 {{
      margin: 2px 0 7px;
      color: #fff;
      font-size: 20px;
      text-align: center;
    }}
    .speed-hero p {{
      margin: 0;
      color: #c9d1e1;
      font-size: 15px;
      line-height: 1.58;
      text-align: center;
    }}
    .speed-list {{
      display: grid;
      gap: 11px;
    }}
    .speed-row {{
      display: grid;
      grid-template-columns: minmax(110px, 1fr) 1.2fr 34px;
      gap: 12px;
      align-items: center;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(20, 25, 39, .62);
    }}
    .speed-row strong {{
      color: #fff;
      font-size: 15px;
    }}
    .speed-row p {{
      margin: 3px 0 0;
      color: #aeb9cc;
      font-size: 12px;
      line-height: 1.35;
    }}
    .speed-meter {{
      height: 9px;
      border-radius: 999px;
      background: rgba(255,255,255,.12);
      overflow: hidden;
    }}
    .speed-meter i {{
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #15d4b3, #20a8ff);
    }}
    .speed-row b {{
      color: #22b7ff;
      text-align: right;
      font-size: 13px;
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
    .report-header {{
      position: relative;
      min-height: 112px;
      padding: 12px 8px 20px;
      color: #fff;
      text-align: left;
    }}
    .report-header::before {{
      content: "";
      position: absolute;
      inset: -42px -20px auto;
      height: 170px;
      background:
        radial-gradient(circle at 17% 42%, rgba(255,255,255,.24) 0 2px, transparent 3px),
        radial-gradient(circle at 74% 22%, rgba(255,255,255,.28) 0 3px, transparent 4px),
        linear-gradient(135deg, rgba(124, 188, 255, .55), rgba(82, 118, 238, .08));
      opacity: .8;
      pointer-events: none;
    }}
    .report-title {{
      position: relative;
      margin: 0;
      font-size: 34px;
      line-height: 1.08;
      font-weight: 950;
      color: #fff;
      text-shadow: 0 8px 22px rgba(38, 70, 150, .24);
    }}
    .report-subtitle {{
      position: relative;
      margin: 4px 0 0;
      color: rgba(255,255,255,.78);
      font-size: 20px;
      font-weight: 800;
      font-style: italic;
    }}
    body {{
      background: #6594f2;
      color: #26345c;
    }}
    .page {{
      width: min(100%, 760px);
      padding: 20px 22px 48px;
      background:
        radial-gradient(circle at 8% 8%, rgba(255,255,255,.22) 0 2px, transparent 3px),
        radial-gradient(circle at 90% 12%, rgba(255,255,255,.22) 0 2px, transparent 3px),
        linear-gradient(180deg, #6594f2 0%, #5d8ef0 48%, #5f91ee 100%);
    }}
    .panel {{
      overflow: visible;
      border-radius: 11px;
      background: rgba(255,255,255,.96);
      border: 1px solid rgba(255,255,255,.75);
      box-shadow: 0 9px 18px rgba(50, 91, 178, .16);
      margin-bottom: 18px;
      color: #324068;
    }}
    .section-body, .analysis-card {{
      padding: 0 28px 26px;
    }}
    .section-title,
    .analysis-card .eyebrow,
    .replay::before {{
      display: flex;
      align-items: center;
      justify-content: center;
      width: 230px;
      max-width: calc(100% - 56px);
      min-height: 48px;
      margin: 0 auto 20px;
      padding: 9px 18px 8px;
      border-radius: 0 0 18px 18px;
      background: linear-gradient(180deg, #eefaff, #d9f3ff);
      color: #496cae;
      font-size: 20px;
      font-weight: 950;
      box-shadow: 0 5px 10px rgba(75, 125, 215, .08);
      text-align: center;
      white-space: nowrap;
      overflow: hidden;
      gap: 0;
    }}
    .title-icon {{
      display: none;
      width: 0;
      height: 0;
      overflow: hidden;
      box-shadow: none;
      background: transparent;
    }}
    .analysis-card {{
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 22px;
      align-items: center;
      text-align: left;
    }}
    .analysis-card .eyebrow {{
      grid-column: 1 / -1;
      justify-self: center;
      font-size: 19px;
      margin-bottom: 0;
    }}
    .score-line {{
      grid-row: 2 / span 4;
      justify-self: center;
      width: 186px;
      height: 186px;
      margin: 4px 0 0;
      display: grid;
      place-items: center;
      align-content: center;
      gap: 2px;
      border-radius: 50%;
      background:
        radial-gradient(circle at 50% 50%, #fff 0 56%, transparent 57%),
        conic-gradient(#4768f4 0deg {score_angle}deg, #ffbd4a {score_angle}deg 278deg, #ff754f 278deg 360deg);
      box-shadow: inset 0 0 0 12px rgba(235, 242, 255, .95), 0 8px 20px rgba(75, 105, 210, .18);
    }}
    .score-line strong {{
      color: #405fde;
      font-size: 46px;
      line-height: 1;
      font-weight: 950;
    }}
    .score-line span {{
      color: #526181;
      font-size: 14px;
      font-weight: 900;
    }}
    .stage {{
      margin: 0;
      max-width: none;
      color: #496cae;
      font-size: 16px;
      line-height: 1.55;
      font-weight: 850;
    }}
    .badge {{
      justify-self: start;
      margin: 0;
      padding: 8px 16px;
      border-radius: 999px;
      background: linear-gradient(90deg, #6688ff, #43b9ff);
      font-size: 14px;
      box-shadow: 0 7px 16px rgba(78, 113, 235, .18);
    }}
    .chips {{
      justify-content: flex-start;
      gap: 8px;
      margin: 0;
    }}
    .chip {{
      background: #edf4ff;
      color: #53699a;
      border: 1px solid #dbe8ff;
      font-size: 12px;
      padding: 6px 11px;
    }}
    .chip.primary {{
      background: #e8f8ff;
      color: #2578d8;
    }}
    .analysis-card h1 {{
      margin: 0;
      color: #26345c;
      font-size: 21px;
      line-height: 1.28;
    }}
    .analysis-card p {{
      color: #5f6c89;
      font-size: 14px;
      line-height: 1.7;
    }}
    .analysis-card .main-summary {{
      grid-column: 1 / -1;
      width: min(100%, 560px);
      margin: 4px auto 0;
      text-align: center;
    }}
    .replay {{
      padding: 0 28px 26px;
    }}
    .replay::before {{
      content: "动作片段回放";
      font-size: 19px;
    }}
    .replay-bg {{
      display: none;
    }}
    .replay-label {{
      position: static;
      display: inline-block;
      margin: 0 0 10px;
      padding: 6px 12px;
      border-radius: 999px;
      background: #edf4ff;
      color: #496cae;
      font-size: 13px;
    }}
    .review-shell {{
      width: 100%;
    }}
    .review-shell img, .review-shell video {{
      border-radius: 8px;
      box-shadow: none;
      border: 1px solid #dfe9ff;
      background: #edf4ff;
    }}
    .review-note {{
      width: 100%;
      margin: 12px 0 0;
      background: #f4f8ff;
      color: #516081;
      border: 1px solid #e7efff;
      font-size: 14px;
    }}
    .chain-overlay {{
      width: 100%;
      grid-template-columns: repeat(4, 1fr);
    }}
    .chain-step {{
      min-height: 88px;
      background: #f8fbff;
      border: 1px solid #e5edff;
      box-shadow: none;
    }}
    .chain-step b {{
      background: #5b7cff;
    }}
    .chain-step span {{
      color: #334166;
    }}
    .chain-step small {{
      color: #6a7592;
    }}
    .focus-item, .moment-dark, .insight-card, .speed-hero, .speed-row {{
      background: #f7f9ff;
      border: 1px solid #edf2ff;
      box-shadow: none;
      border-radius: 9px;
    }}
    .focus-item h3, .focus-item h4, .insight-card h3, .moment-dark h3, .moment-dark h4, .speed-hero h3, .speed-row strong {{
      color: #344265;
    }}
    .focus-item p, .moment-dark p, .insight-card p, .speed-hero p, .speed-row p {{
      color: #66718c;
    }}
    .icon-shell {{
      background: #e6f3ff;
      box-shadow: none;
    }}
    .icon-shell svg {{
      stroke: #fff;
      color: #fff;
    }}
    .icon-shell svg path, .icon-shell svg circle, .icon-shell svg line, .icon-shell svg polyline, .icon-shell svg polygon {{
      stroke: #fff;
    }}
    .icon-shell svg [fill]:not([fill="none"]) {{
      fill: #fff;
    }}
    .icon-shell svg [stroke] {{
      stroke: #fff;
    }}
    .radar text {{
      fill: #435179;
    }}
    .metric-row {{
      grid-template-columns: 92px 1fr 42px;
      color: #435179;
    }}
    .metric-track, .speed-meter {{
      height: 11px;
      background: #e6ebf6;
    }}
    .metric-track i, .speed-meter i {{
      background: linear-gradient(90deg, #596bf3, #4eb7ff);
    }}
    .metric-row b, .speed-row b {{
      color: #297bff;
    }}
    .score-note {{
      background: #f3f8ff;
      color: #66718c;
      border: 1px solid #e5efff;
    }}
    .speed-score {{
      background:
        radial-gradient(circle at 50% 50%, #fff 0 54%, transparent 55%),
        conic-gradient(#4e71ff 0deg, #46bdf4 276deg, #e6ebf6 276deg 360deg);
      box-shadow: inset 0 0 0 8px #eef5ff;
    }}
    .speed-score strong {{
      color: #405fde;
    }}
    .time-badge {{
      background: #e7f3ff;
      color: #3477d9;
    }}
    .time-badge span {{
      color: #7f8aa5;
    }}
    @media (max-width: 620px) {{
      .page {{ padding: 34px 13px 28px; }}
      .analysis-card {{ padding: 0 18px 24px; }}
      .score-line strong {{ font-size: 58px; }}
      .score-line span {{ font-size: 20px; }}
      .stage {{ font-size: 17px; }}
      .badge {{ font-size: 15px; padding: 9px 18px; }}
      .analysis-card h1 {{ font-size: 21px; }}
      .analysis-card p {{ font-size: 15px; line-height: 1.55; }}
      .replay {{ padding: 0 12px 18px; }}
      .review-shell, .review-note, .chain-overlay {{ width: 84%; }}
      .review-shell img, .review-shell video {{ border-radius: 10px; }}
      .replay-label {{ left: 58px; top: 20px; font-size: 11px; }}
      .review-note {{ font-size: 12px; padding: 9px 11px; }}
      .chain-overlay {{ grid-template-columns: repeat(2, 1fr); gap: 7px; }}
      .chain-step {{ min-height: 70px; padding: 9px; }}
      .chain-step span {{ font-size: 12px; }}
      .chain-step small {{ font-size: 10px; }}
      .section-body {{ padding: 0 14px 18px; }}
      .section-title, .analysis-card .eyebrow, .replay::before {{
        width: 206px;
        max-width: calc(100% - 44px);
        min-height: 44px;
        margin: 0 auto 18px;
        padding: 8px 14px 7px;
        font-size: 18px;
      }}
      .focus-item, .moment-dark, .insight-card {{ padding: 14px; gap: 11px; }}
      .focus-item p, .moment-dark p, .insight-card p {{ font-size: 13px; }}
      .focus-item h3, .insight-card h3, .moment-dark h3 {{ font-size: 16px; }}
      .focus-item h4, .moment-dark h4 {{ font-size: 14px; }}
      .metric-row {{ grid-template-columns: 72px 1fr 28px; font-size: 12px; }}
      .time-badge {{ width: 49px; font-size: 11px; }}
      .speed-hero {{ grid-template-columns: 1fr; gap: 12px; padding: 14px; text-align: center; justify-items: center; }}
      .speed-score {{ width: 76px; height: 76px; justify-self: center; }}
      .speed-score strong {{ font-size: 23px; }}
      .speed-hero h3 {{ font-size: 16px; text-align: center; }}
      .speed-hero p {{ font-size: 13px; text-align: center; }}
      .speed-row {{ grid-template-columns: 1fr; gap: 8px; padding: 12px; }}
      .speed-row b {{ text-align: left; }}
      .report-header {{ min-height: 96px; padding: 8px 4px 16px; }}
      .report-title {{ font-size: 28px; }}
      .report-subtitle {{ font-size: 17px; }}
      .analysis-card {{ grid-template-columns: 1fr; text-align: center; gap: 14px; }}
      .analysis-card .main-summary {{ grid-column: auto; width: 100%; }}
      .analysis-card .eyebrow {{ font-size: 17px; margin-bottom: 0; }}
      .score-line {{ grid-row: auto; width: 156px; height: 156px; justify-self: center; }}
      .score-line strong {{ font-size: 40px; }}
      .score-line span {{ font-size: 13px; }}
      .stage {{ font-size: 14px; }}
      .badge {{ justify-self: center; }}
      .chips {{ justify-content: center; }}
      .chain-overlay {{ width: 100%; grid-template-columns: repeat(2, 1fr); }}
      .replay-label {{ position: static; font-size: 12px; }}
      .review-shell, .review-note {{ width: 100%; }}
      .metric-row {{ grid-template-columns: 76px 1fr 30px; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header class="report-header">
      <h1 class="report-title">网球动作能力测试</h1>
      <p class="report-subtitle">Tennis Movement Test</p>
    </header>

    <section class="panel analysis-card">
      <p class="eyebrow">测评得分</p>
      <div class="score-line"><strong>{score}</strong><span>/100</span></div>
      <p class="stage">已进入{esc(stage)}，本评分基于准备启动、动力链传导、击球时机、挥速释放、随挥回收与身体稳定的综合动作评定。</p>
      <div class="badge">{icon_svg("chain")}动作链综合评定</div>
      <div class="chips">
        <span class="chip primary">进阶</span>
        <span class="chip">{esc(ntrp)}</span>
        <span class="chip">{esc(confidence)}</span>
      </div>
      <h1>{esc(headline)}</h1>
      <p class="main-summary">{esc(main_body)}</p>
    </section>

    <section class="panel">
      <div class="section-body">
        <h2 class="section-title"><span class="title-icon">{icon_svg("radar")}</span>动作能力分项</h2>
        <div class="radar-wrap">
          {radar_svg(metrics)}
          <div class="metric-list">{render_metric_bars(metrics)}</div>
          <p class="score-note">{esc(score_note)}</p>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="section-body">
        <h2 class="section-title"><span class="title-icon">{icon_svg("target")}</span>技能点得分分析</h2>
        <div class="focus-list">{render_focus_blocks(data)}</div>
      </div>
    </section>

    {render_swing_speed(data)}
    
    <section class="panel">
      <div class="section-body">
        <h2 class="section-title"><span class="title-icon">{icon_svg("clock")}</span>关键片段分析</h2>
        <div class="moment-list">{render_key_moments_dark(data)}</div>
      </div>
    </section>

    <section class="panel">
      <div class="section-body">
        <h2 class="section-title"><span class="title-icon">{icon_svg("insight")}</span>教练反馈</h2>
        <div class="insight-list">{render_insights_dark(data)}</div>
      </div>
    </section>

    <section class="panel replay">
      <div class="replay-bg"></div>
      <div class="replay-label">{esc(review_title)}</div>
      <div class="review-shell">{review_media_html}</div>
      <div class="review-note">{esc(review_issue)}</div>
      <div class="chain-overlay">{render_chain_steps(data)}</div>
    </section>
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

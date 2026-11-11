#!/usr/bin/env python3
"""留存节奏 QA：对导出的竖屏口播成片做可量化体检。

用法:
  python3 retention_qa.py <video.mp4> [--out DIR] [--scene 0.06] [--static 4.0]

输出（打印 + DIR/retention_qa.json + DIR/contact_sheet.jpg）:
  - visual_events: 画面事件时间点（硬切、推拉跳变、整屏卡片/补镜进出）
  - gaps: 相邻事件间隔；longest_static: 最长无变化段；static_spans: 超过阈值的段
  - hook: 0–3 秒内的事件数
  - loudness: Integrated LUFS / True Peak / LRA
  - verdict: 按 SKILL 中的留存目标逐项 PASS / WARN

只依赖 ffmpeg/ffprobe。场景阈值对口播偏低（0.06），能捕捉 110% 以上的推拉跳变和
整屏 MG；慢推（slow push）这类连续运动不会被计为事件，这是刻意的——它只算“持续运动”，
不算“节奏点”。
"""
import argparse, json, os, re, subprocess, sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def duration(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(r.stdout.strip())


def scene_events(path, thr):
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-an", "-vf",
             f"scale=270:-2,select='gt(scene,{thr})',showinfo", "-f", "null", "-"])
    times = [float(m) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    merged = []
    for t in times:  # 0.4s 内的连续触发算一次事件（转场动画会连触多帧）
        if not merged or t - merged[-1] > 0.4:
            merged.append(round(t, 2))
    return merged


def loudness(path):
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    def grab(label):
        m = re.search(label + r":\s+(-?[0-9.]+)", tail)
        return float(m.group(1)) if m else None
    return {"integrated_lufs": grab("I"), "lra": grab("LRA"), "true_peak_dbfs": grab("Peak")}


def contact_sheet(path, out, dur):
    n = 24
    fps = n / max(dur, 1)
    run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf",
         f"fps={fps:.5f},scale=180:-2,drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.5,tile=8x3",
         "-frames:v", "1", out])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", default=None)
    ap.add_argument("--scene", type=float, default=0.06)
    ap.add_argument("--static", type=float, default=4.0, help="静态段告警阈值（秒）")
    ap.add_argument("--exempt", default="", help="豁免区间（秒），如 23-28.5,54.7-60.8：示意图/演示定格段不计入静态段")
    a = ap.parse_args()
    out = a.out or os.path.splitext(a.video)[0] + "_qa"
    os.makedirs(out, exist_ok=True)

    dur = duration(a.video)
    ev = scene_events(a.video, a.scene)
    pts = [0.0] + ev + [dur]
    gaps = [round(pts[i + 1] - pts[i], 2) for i in range(len(pts) - 1)]
    exempt = []
    for part in filter(None, a.exempt.split(",")):
        x, y = part.split("-")
        exempt.append((float(x), float(y)))

    def covered(f, t):  # 静态段与豁免区间重叠超过一半时视为豁免
        ov = sum(max(0, min(t, y) - max(f, x)) for x, y in exempt)
        return ov >= 0.5 * (t - f)

    spans = [{"from": pts[i], "to": pts[i + 1], "sec": gaps[i]} for i in range(len(gaps))
             if gaps[i] > a.static and not covered(pts[i], pts[i + 1])]
    counted = [gaps[i] for i in range(len(gaps)) if not covered(pts[i], pts[i + 1])]
    longest = max(counted) if counted else 0.0
    hook_events = len([t for t in ev if t <= 3.0])
    loud = loudness(a.video)
    per_min = round(len(ev) / dur * 60, 1)
    avg_gap = round(dur / (len(ev) + 1), 2)
    static_ratio = round(sum(s["sec"] for s in spans) / dur, 3)

    def v(ok, warn_text):
        return "PASS" if ok else "WARN: " + warn_text

    lufs = loud["integrated_lufs"]
    verdict = {
        "avg_visual_gap<=3.5s": v(avg_gap <= 3.5, f"平均 {avg_gap}s 才有一次画面变化"),
        f"longest_static<={a.static + 2:.0f}s": v(longest <= a.static + 2, f"最长静态段 {longest}s"),
        "static_ratio<=15%": v(static_ratio <= 0.15, f"{static_ratio*100:.0f}% 时长处于>{a.static}s 的静态段"),
        "hook_events>=2_in_3s": v(hook_events >= 2, f"前 3 秒只有 {hook_events} 次画面变化"),
        "loudness_-16..-13LUFS": v(lufs is not None and -16.5 <= lufs <= -12.5, f"整体响度 {lufs} LUFS"),
        "true_peak<=-1dBTP": v(loud["true_peak_dbfs"] is not None and loud["true_peak_dbfs"] <= -1.0,
                               f"真峰值 {loud['true_peak_dbfs']} dBTP"),
    }
    report = {"video": a.video, "exempt": exempt, "duration": round(dur, 2), "visual_events": ev,
              "events_per_min": per_min, "avg_gap": avg_gap, "longest_static": longest,
              "static_spans": spans, "static_ratio": static_ratio, "hook_events_0_3s": hook_events,
              "loudness": loud, "verdict": verdict}
    with open(os.path.join(out, "retention_qa.json"), "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    contact_sheet(a.video, os.path.join(out, "contact_sheet.jpg"), dur)

    print(f"时长 {dur:.1f}s | 画面事件 {len(ev)} 次 ({per_min}/min) | 平均间隔 {avg_gap}s | 最长静态 {longest}s")
    print(f"前3秒事件 {hook_events} | 静态占比 {static_ratio*100:.0f}% | 响度 {lufs} LUFS / TP {loud['true_peak_dbfs']}")
    for s in spans:
        print(f"  静态段 {s['from']:.1f}s → {s['to']:.1f}s ({s['sec']}s)")
    for k, val in verdict.items():
        print(f"[{k}] {val}")
    print("报告:", out)


if __name__ == "__main__":
    sys.exit(main())

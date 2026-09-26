"""First-pass quality check of every clip — free, local, measurements only (ffmpeg). Writes qa.json.

Flags what a listener would notice:
  lead_silence   > 0.5 s of silence before the first word (a bot feels slow)
  cut_off        speech still loud in the last 50 ms (ending chopped)
  clipping       peak at or above -0.3 dBFS (distortion)
  long_pause     a silence > 1.5 s inside the line
  too_fast/slow  speaking rate > 1.35x or < 0.7x the median of all models on the same line
  words          transcript error rate >= 15% (skipped / added / wrong words), Urdu-script transcripts excluded
  tags_aloud     the AI listener heard a stage direction spoken as words
"""
import glob
import json
import os
import re
import statistics
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out-voice")
PROMPTS = json.load(open(os.path.join(HERE, "prompts.json")))
TEXT = {p["id"]: p["text"] for p in PROMPTS["prompts"]}
for c in PROMPTS["clone"]["tests"]:
    TEXT[c["id"]] = c["text"]


def ff(path, filt):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", filt, "-f", "null", "-"],
                          capture_output=True, text=True).stderr


def measure(path):
    s = ff(path, "silencedetect=noise=-45dB:d=0.25")
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", s)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", s)]
    dur = re.findall(r"Duration: (\d+):(\d+):([\d.]+)", s)
    d = int(dur[0][0]) * 3600 + int(dur[0][1]) * 60 + float(dur[0][2]) if dur else 0
    lead = 0.0
    if starts and starts[0] <= 0.02 and ends:
        lead = ends[0]
    inner = [e - st for st, e in zip(starts, ends) if st > 0.05 and e < d - 0.05]
    a = ff(path, "astats=metadata=0:reset=0")
    pk = re.findall(r"Peak level dB: (-?[\d.]+|-inf)", a)
    peak = max(float(x) for x in pk if x != "-inf") if pk else None
    tail = ff(path, "atrim=start=%f,astats" % max(0, d - 0.05))
    tail_rms = re.findall(r"RMS level dB: (-?[\d.]+|-inf)", tail)
    tail_db = max((float(x) for x in tail_rms if x != "-inf"), default=-120.0)
    trailing = d - starts[-1] if starts and (not ends or starts[-1] > ends[-1]) else 0.0
    return {"dur": round(d, 2), "lead": round(lead, 2), "max_pause": round(max(inner), 2) if inner else 0.0,
            "peak_db": peak, "tail_db": round(tail_db, 1), "trailing_silence": round(trailing, 2)}


def main():
    scores = {}
    for l in open(os.path.join(HERE, "scores.jsonl")):
        r = json.loads(l)
        if r.get("judge") or (r["model"], r["prompt"]) not in scores:
            scores[(r["model"], r["prompt"])] = r
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT, "*", "*.*"))):
        m = os.path.basename(os.path.dirname(f))
        pid = os.path.splitext(os.path.basename(f))[0]
        if m.startswith("_") or "_r" in pid or pid not in TEXT:
            continue
        x = measure(f)
        x.update(model=m, prompt=pid, rate=round(len(re.sub(r"\s", "", TEXT[pid])) / max(0.1, x["dur"] - x["lead"]
                                                                                        - x["trailing_silence"]), 2))
        s = scores.get((m, pid), {})
        t = s.get("transcript") or ""
        urdu = sum(1 for ch in t if "؀" <= ch <= "ۿ") > 0.3 * max(1, sum(ch.isalpha() for ch in t))
        x["cer"] = None if urdu else s.get("cer")
        x["tags_aloud"] = bool((s.get("judge") or {}).get("read_tags_aloud"))
        rows.append(x)
    med = {}
    for pid in TEXT:
        rs = [r["rate"] for r in rows if r["prompt"] == pid]
        if rs:
            med[pid] = statistics.median(rs)
    for r in rows:
        flags = []
        if r["lead"] > 0.5:
            flags.append("lead_silence %.1fs" % r["lead"])
        if r["tail_db"] > -30 and r["trailing_silence"] < 0.05:
            flags.append("cut_off (tail %.0f dB)" % r["tail_db"])
        if r["peak_db"] is not None and r["peak_db"] >= -0.3:
            flags.append("clipping (peak %.1f dBFS)" % r["peak_db"])
        if r["max_pause"] > 1.5:
            flags.append("long_pause %.1fs" % r["max_pause"])
        ratio = r["rate"] / med[r["prompt"]]
        r["rate_vs_median"] = round(ratio, 2)
        if ratio > 1.35:
            flags.append("too_fast %.2fx" % ratio)
        if ratio < 0.7:
            flags.append("too_slow %.2fx" % ratio)
        if r["cer"] is not None and r["cer"] >= 0.15:
            flags.append("words %d%% wrong" % round(r["cer"] * 100))
        if r["tags_aloud"]:
            flags.append("tags_aloud")
        r["flags"] = flags
    json.dump(rows, open(os.path.join(HERE, "qa.json"), "w"), ensure_ascii=False, indent=0)
    by = {}
    for r in rows:
        by.setdefault(r["model"], []).append(r)
    print("%-38s %5s %6s  %s" % ("model", "clips", "clean", "problems"))
    for m, rs in sorted(by.items(), key=lambda kv: -sum(1 for r in kv[1] if not r["flags"]) / len(kv[1])):
        clean = sum(1 for r in rs if not r["flags"])
        probs = ["%s: %s" % (r["prompt"], ", ".join(r["flags"])) for r in rs if r["flags"]]
        print("%-38s %5d %6d  %s" % (m, len(rs), clean, " | ".join(probs)[:400]))


if __name__ == "__main__":
    main()

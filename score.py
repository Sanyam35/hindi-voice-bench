"""Score every clip in out-voice/ on separate dimensions (no single number).

  python3 score.py --dry-run            # lists clips to score + estimated cost
  python3 score.py --budget 1.00        # paid: transcribe + AI-listener; free: loudness/duration

Per clip it records (scores.jsonl, one line per clip; never re-scores a clip already scored):
  1. duration, integrated loudness (LUFS), peak (ffmpeg, free)
  2. round-trip transcript (OpenAI gpt-4o-transcribe, language=hi) and character error rate vs the script
     for the pure-Hindi lines — a proxy for "can a listener understand every word"
  3. an AI listener (Gemini 3.1 Pro, hears the audio) ticking the prompt's checklist and rating
     naturalness / emotion 1-5. It is an AI ear, not a human one — Sanyam's listen is the final word.
"""
import argparse
import base64
import glob
import json
import os
import re
import subprocess
import time
import unicodedata
import urllib.request
import uuid

from voice_bench import HERE, PROMPTS, keys

OUT = os.path.join(HERE, "out-voice")
SCORES = os.path.join(HERE, "scores.jsonl")
JUDGE = "gemini-3.1-pro-preview"
PURE_HINDI = {"V1", "V3", "V4", "V5", "C1", "C2"}
PMAP = {p["id"]: p for p in PROMPTS["prompts"]}
for c in PROMPTS["clone"]["tests"]:
    PMAP[c["id"]] = {"id": c["id"], "text": c["text"], "emotion": c.get("emotion", "calm, reflective"),
                     "checklist": PROMPTS["clone"]["checklist"]}
PMAP["S1"] = dict(PMAP["V5"], id="S1")


def norm(s):
    s = unicodedata.normalize("NFD", s)
    s = s.replace("\u093c", "")  # drop nukta: ज़ vs ज is judged by the AI listener, not by CER
    s = re.sub(r"[\u0901\u0902]", "\u0902", s)  # chandrabindu ~ anusvara
    s = re.sub(r"[^\w\u0900-\u097f]+", "", s.lower())
    return re.sub(r"[\u0964\u0965]", "", s)


def cer(ref, hyp):
    a, b = norm(ref), norm(hyp)
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (ca != cb))
    return round(d[len(b)] / max(1, len(a)), 3)


def acoustics(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    txt = r.stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", txt)
    pk = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", txt)
    dur = re.findall(r"Duration: (\d+):(\d+):([\d.]+)", txt)
    d = None
    if dur:
        h, mi, s = dur[0]
        d = int(h) * 3600 + int(mi) * 60 + float(s)
    return {"duration_s": round(d, 2) if d else None, "lufs": float(i[-1]) if i else None,
            "peak_dbfs": float(pk[-1]) if pk else None}


def to_mp3_bytes(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "mp3", "-"],
                       capture_output=True)
    return r.stdout


def transcribe(key, path):
    audio = to_mp3_bytes(path)
    b = uuid.uuid4().hex
    parts = []
    for name, val in [("model", "gpt-4o-transcribe"), ("language", "hi")]:
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b, name, val)).encode())
    parts.append(("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.mp3\"\r\n"
                  "Content-Type: audio/mpeg\r\n\r\n" % b).encode() + audio + b"\r\n")
    parts.append(("--%s--\r\n" % b).encode())
    req = urllib.request.Request("https://api.openai.com/v1/audio/transcriptions", data=b"".join(parts), method="POST",
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "multipart/form-data; boundary=" + b})
    return json.load(urllib.request.urlopen(req, timeout=120))["text"]


def judge(key, path, p, ref_path=None):
    items = "\n".join("%d. %s" % (i + 1, c) for i, c in enumerate(p["checklist"]))
    ask = (
        "You are a strict native Hindi listener and voice director judging a text-to-speech clip for a Hindi "
        "audio drama. The script was:\n%s\nIntended delivery: %s.\n\nChecklist:\n%s\n\n"
        "Listen carefully. Return ONLY JSON: {\"checklist\": [true/false per item in order], "
        "\"naturalness\": 1-5 (5 = indistinguishable from a native human actor), "
        "\"emotion\": 1-5 (5 = the intended delivery is fully convincing), "
        "\"pronunciation_errors\": [short list of mispronounced/skipped/added words, quote them], "
        "\"read_tags_aloud\": true/false (did it speak stage directions or bracket tags as words), "
        "\"artifacts\": [glitches, clicks, robotic bits, wrong language, cut-offs], "
        "\"note\": one plain-English sentence}" % (p["text"], p.get("emotion", "neutral"), items))
    parts = [{"text": ask}, {"inlineData": {"mimeType": "audio/mp3", "data": base64.b64encode(to_mp3_bytes(path)).decode()}}]
    if ref_path:
        parts.insert(0, {"text": "First, the REFERENCE voice the clip should sound like. Also add "
                                 "\"similarity\": 1-5 (5 = clearly the same person as the reference) to the JSON."})
        parts.insert(1, {"inlineData": {"mimeType": "audio/mp3",
                                        "data": base64.b64encode(to_mp3_bytes(ref_path)).decode()}})
    body = {"contents": [{"parts": parts}], "generationConfig": {"responseMimeType": "application/json",
                                                                 "temperature": 0}}
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % JUDGE
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    res = json.load(urllib.request.urlopen(req, timeout=180))
    txt = "".join(pt.get("text", "") for pt in res["candidates"][0]["content"]["parts"] if not pt.get("thought"))
    return json.loads(txt), res.get("usageMetadata", {})


EXTRA = os.path.join(HERE, "extra_scores.jsonl")


def phone_version(path):
    """Squeeze a clip through a phone line: 8 kHz mu-law, like a Retell PSTN call."""
    tmp = os.path.join(OUT, "_phone", os.path.basename(os.path.dirname(path)) + "__" + os.path.basename(path) + ".wav")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", "8000", "-acodec", "pcm_mulaw", tmp],
                   check=True)
    return tmp


def consistency(key, files):
    parts = [{"text": "Three clips from one text-to-speech voice, meant to be the SAME character acting different "
                      "emotions. Return ONLY JSON: {\"same_speaker\": 1-5 (5 = unmistakably the same person in every "
                      "clip; lower if timbre, age, accent or gender drifts), \"drift\": one plain-English sentence}"}]
    for f in files:
        parts.append({"inlineData": {"mimeType": "audio/mp3", "data": base64.b64encode(to_mp3_bytes(f)).decode()}})
    body = {"contents": [{"parts": parts}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % JUDGE
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    res = json.load(urllib.request.urlopen(req, timeout=180))
    txt = "".join(pt.get("text", "") for pt in res["candidates"][0]["content"]["parts"] if not pt.get("thought"))
    return json.loads(txt)


def extras(K, budget):
    """Per model: voice consistency across emotions + phone-line intelligibility. Never repeats a done model."""
    done = set()
    if os.path.exists(EXTRA):
        done = {json.loads(l)["model"] for l in open(EXTRA)}
    spent = 0.0
    for d in sorted(glob.glob(os.path.join(OUT, "*"))):
        m = os.path.basename(d)
        if m.startswith("_") or m in done:
            continue
        pick = lambda ids: [f for i in ids for f in glob.glob(os.path.join(d, i + ".*"))][:3]
        # three clips of the SAME character: Raghu (V-lines) or Dadi (C-lines), never mixed
        trio = next((pick(ids) for ids in (["V1", "V4", "V5"], ["V3", "V4", "V5"], ["V3", "V5", "V2"], ["C1", "C2"])
                     if len(pick(ids)) >= min(3, len(ids))), [])
        if m.startswith(("hf__rumik", "mac__rumik")):  # preset voice 'Ira' on every line
            trio = pick(["C1", "C2", "V3"])
        base = (pick(["V1"]) or pick(["C1"]))[:1]
        if spent + 0.02 > budget:
            print("STOP extras: budget")
            break
        rec = {"model": m}
        if len(trio) >= 2:
            try:
                rec["consistency"] = consistency(K["gemini"], trio)
                rec["consistency_clips"] = [os.path.basename(f) for f in trio]
            except Exception as e:  # noqa: BLE001
                rec["consistency_error"] = str(e)[:200]
        if base:
            pid = os.path.splitext(os.path.basename(base[0]))[0]
            try:
                t = transcribe(K["openai"], phone_version(base[0]))
                rec["phone"] = {"clip": pid, "transcript": t, "cer": cer(PMAP[pid]["text"], t)}
            except Exception as e:  # noqa: BLE001
                rec["phone_error"] = str(e)[:200]
        spent += 0.02
        with open(EXTRA, "a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("%-36s same_speaker=%s phone_cer=%s" % (m, (rec.get("consistency") or {}).get("same_speaker"),
                                                     (rec.get("phone") or {}).get("cer")))
    return spent


def clips():
    for path in sorted(glob.glob(os.path.join(OUT, "*", "*.*"))):
        pid = os.path.splitext(os.path.basename(path))[0]
        if pid.startswith("_") or "_r" in pid or os.path.basename(os.path.dirname(path)).startswith("_"):
            continue  # latency repeats and reference files are not scored
        base = pid.split("-")[0]
        if base in PMAP:
            yield os.path.basename(os.path.dirname(path)), base, path


LOCK = os.path.join(HERE, "score.lock")


def wait_for_other_scorer():
    """Two scorers at once would pay twice for the same clips: wait for any other live score.py to finish."""
    me = os.getpid()
    while True:
        r = subprocess.run(["pgrep", "-f", "score.py"], capture_output=True, text=True)
        others = [int(p) for p in r.stdout.split() if p.strip() and int(p) != me and int(p) != os.getppid()]
        others = [p for p in others if "score.py" in subprocess.run(["ps", "-o", "command=", "-p", str(p)],
                                                                      capture_output=True, text=True).stdout
                  and "python" in subprocess.run(["ps", "-o", "command=", "-p", str(p)],
                                                 capture_output=True, text=True).stdout.lower()]
        if not others:
            return
        print("Another scoring run is still going (pid %s) — waiting so no clip is paid for twice..." % others[0],
              flush=True)
        time.sleep(30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=0.0)
    a = ap.parse_args()
    if not a.dry_run:
        wait_for_other_scorer()
    done = set()
    if os.path.exists(SCORES):
        for line in open(SCORES):
            r = json.loads(line)
            if r.get("judge"):  # a clip whose AI-listener call failed is scored again next run
                done.add((r["model"], r["prompt"]))
    todo = [(m, p, f) for m, p, f in clips() if (m, p) not in done]
    est = 0.012 * len(todo)  # ~$0.002 transcribe + ~$0.01 judge per clip (conservative)
    print("To score: %d clips (%d already scored). Estimated $%.2f." % (len(todo), len(done), est))
    if a.dry_run:
        return
    K = keys()
    ref = os.path.join(OUT, "_reference", "dadi.wav")
    spent = 0.0
    for m, pid, f in todo:
        if spent + 0.012 > a.budget:
            print("STOP: budget reached at $%.2f" % spent)
            break
        p = PMAP[pid]
        rec = {"model": m, "prompt": pid, "file": os.path.relpath(f, HERE)}
        rec.update(acoustics(f))
        try:
            rec["transcript"] = transcribe(K["openai"], f)
            if pid in PURE_HINDI:
                rec["cer"] = cer(p["text"], rec["transcript"])
        except Exception as e:  # noqa: BLE001
            rec["transcript_error"] = str(e)[:200]
        try:
            j, u = judge(K["gemini"], f, p, ref if pid.startswith("C") else None)
            rec["judge"] = j
            rec["judge_usage"] = u
        except Exception as e:  # noqa: BLE001
            rec["judge_error"] = str(e)[:300]
        spent += 0.012
        with open(SCORES, "a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        jj = rec.get("judge", {})
        print("%-36s %-3s cer=%s nat=%s emo=%s %s" % (m, pid, rec.get("cer"), jj.get("naturalness"),
                                                   jj.get("emotion"), (jj.get("note") or rec.get("judge_error", ""))[:70]))
        time.sleep(0.5)
    spent += extras(K, a.budget - spent)
    print("Scoring spend (est.): $%.2f" % spent)


if __name__ == "__main__":
    main()

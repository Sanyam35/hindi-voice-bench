"""Open voice models on this Mac (Apple Silicon, mlx-audio). Free; one model per process to spare the 16 GB.

  .venv/bin/python local_bench.py kokoro
  .venv/bin/python local_bench.py chatterbox
  .venv/bin/python local_bench.py voxcpm2
  .venv/bin/python local_bench.py rumik

Cloning models copy two synthetic references (never a real person):
  Dadi  = out-voice/_reference/dadi.wav (Gemini voice)            -> C1, C2
  Raghu = out-voice/google__gemini-3.8-flash-tts/V1.wav (Gemini)  -> V2-V6, V8 (tests acting + same-voice)
Records per clip: load time, generation time, audio length, real-time factor, peak memory. Never remakes a clip.
"""
import json
import os
import sys
import time

os.environ.setdefault("HF_HUB_CACHE", os.path.expanduser("~/projects/model-lab/models/voice/hub"))

import mlx.core as mx  # noqa: E402
import numpy as np  # noqa: E402
from mlx_audio.audio_io import write as audio_write  # noqa: E402
from mlx_audio.tts.generate import generate_audio  # noqa: E402,F401  (kept for parity with the CLI)
from mlx_audio.tts.utils import load_model  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out-voice")
RECEIPTS = os.path.join(HERE, "receipts.jsonl")
PROMPTS = json.load(open(os.path.join(HERE, "prompts.json")))
P = {p["id"]: p for p in PROMPTS["prompts"]}
for c in PROMPTS["clone"]["tests"]:
    P[c["id"]] = {"id": c["id"], "text": c["text"], "emotion": c.get("emotion", "calm, reflective")}
DADI = os.path.join(OUT, "_reference", "dadi.wav")
DADI_TEXT = PROMPTS["clone"]["reference_text"]
RAGHU = os.path.join(OUT, "google__gemini-3.8-flash-tts", "V1.wav")
RAGHU_TEXT = P["V1"]["text"]
CLONE_LINES = ["C1", "C2", "V3", "V4", "V5", "V6", "V2", "V8"]
RUMIK_TONE = {"C1": "calm", "C2": "angry", "V3": "whispering, scared", "V6": "steady", "V2": "tired, conversational",
              "V7": "happy, warm, talking to a child", "V8": "fond, laughing"}
RUMIK_TEXT = {"V8": "<laugh> अरे पागल! तुम भी ना… <sigh> चलो, अब सो जाओ। कल बहुत लंबा दिन है।"}

MODELS = {
    "kokoro": {"key": "mac__kokoro-82m", "repo": "mlx-community/Kokoro-82M-bf16",
               "lines": ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"],
               "kw": lambda pid: {"voice": "hf_alpha" if pid == "V7" else "hm_omega", "lang_code": "h"}},
    "chatterbox": {"key": "mac__chatterbox-multilingual-v3", "repo": "mlx-community/chatterbox-multilingual-v3",
                   "lines": CLONE_LINES, "clone": True,
                   "kw": lambda pid: {"lang_code": "hi", "exaggeration": 0.8 if pid in ("C2", "V4", "V5") else 0.5,
                                      "cfg_weight": 0.5}},
    "voxcpm2": {"key": "mac__voxcpm2-8bit", "repo": "mlx-community/VoxCPM2-8bit", "lines": CLONE_LINES, "clone": True,
                "kw": lambda pid: {"instruct": P[pid]["emotion"]} if pid not in ("C1", "V6") else {}},
    "rumik": {"key": "mac__rumik-oss-1-4bit", "repo": "rumik-ai/rumik-oss-1-mlx-4bit",
              "lines": ["C1", "C2", "V3", "V6", "V2", "V7", "V8"],
              "kw": lambda pid: {"voice": "Ira", "instruct": RUMIK_TONE.get(pid, "calm") + ", Hindi accent, steady pace"}},
}


def log(rec):
    with open(RECEIPTS, "a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def say(name, text, who="raghu", style=None):
    """Try any line: .venv/bin/python local_bench.py voxcpm2 --say "..." [--voice dadi] [--style "angry"]"""
    cfg = MODELS[name]
    t0 = time.time()
    model = load_model(cfg["repo"])
    print("loaded in %.1fs" % (time.time() - t0), flush=True)
    kw = dict(cfg["kw"]("V1"))
    if style:
        kw["instruct"] = style
    if cfg.get("clone"):
        from mlx_audio.utils import load_audio
        ref, ref_text = (DADI, DADI_TEXT) if who == "dadi" else (RAGHU, RAGHU_TEXT)
        kw.update(ref_audio=load_audio(ref, sample_rate=model.sample_rate), ref_text=ref_text)
    t1 = time.time()
    chunks = [np.array(r.audio) for r in model.generate(text=text, verbose=False, **kw)]
    audio = np.concatenate(chunks)
    os.makedirs(os.path.join(OUT, "_try"), exist_ok=True)
    path = os.path.join(OUT, "_try", "%s-%s.wav" % (name, time.strftime("%H%M%S")))
    audio_write(path, audio, model.sample_rate, format="wav")
    dur = len(audio) / float(model.sample_rate)
    print("made %.1fs of speech in %.1fs -> %s" % (dur, time.time() - t1, path), flush=True)
    if not os.environ.get("NO_PLAY"):
        os.system('afplay "%s"' % path)


def main():
    if "--say" in sys.argv:
        a = sys.argv
        get = lambda f, d=None: a[a.index(f) + 1] if f in a else d
        return say(a[1], get("--say"), get("--voice", "raghu"), get("--style"))
    name = sys.argv[1]
    cfg = MODELS[name]
    todo = [pid for pid in cfg["lines"] if not os.path.exists(os.path.join(OUT, cfg["key"], pid + ".wav"))]
    if not todo:
        print("all clips exist")
        return
    if cfg.get("clone") and not (os.path.exists(DADI) and os.path.exists(RAGHU)):
        sys.exit("Needs the two synthetic references first (run_paid.sh makes them).")
    t0 = time.time()
    model = load_model(cfg["repo"])
    load_s = round(time.time() - t0, 1)
    print("%s loaded in %.1fs" % (cfg["key"], load_s), flush=True)
    os.makedirs(os.path.join(OUT, cfg["key"]), exist_ok=True)
    for pid in todo:
        text = RUMIK_TEXT.get(pid, P[pid]["text"]) if name == "rumik" else P[pid]["text"]
        kw = dict(cfg["kw"](pid))
        if cfg.get("clone"):
            ref, ref_text = (DADI, DADI_TEXT) if pid.startswith("C") else (RAGHU, RAGHU_TEXT)
            kw.update(ref_audio=ref, ref_text=ref_text)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": cfg["key"], "prompt": pid, "cost_usd": 0,
               "sent_text": text, "voice": kw.get("voice") or ("clone of " + os.path.basename(kw.get("ref_audio", ""))),
               "style": kw.get("instruct"), "load_s": load_s, "device": "MacBook M5 16 GB (mlx-audio)"}
        mx.reset_peak_memory()
        t1 = time.time()
        try:
            gen_kw = {k: v for k, v in kw.items() if k != "ref_audio"}
            if "ref_audio" in kw:
                from mlx_audio.utils import load_audio
                gen_kw["ref_audio"] = load_audio(kw["ref_audio"], sample_rate=model.sample_rate)
            chunks, first, sr = [], None, model.sample_rate
            for res in model.generate(text=text, verbose=False, **gen_kw):
                if first is None:
                    first = time.time() - t1
                chunks.append(np.array(res.audio))
                sr = getattr(res, "sample_rate", sr) or sr
            audio = np.concatenate(chunks) if chunks else np.zeros(0)
            path = os.path.join(OUT, cfg["key"], pid + ".wav")
            audio_write(path, audio, sr, format="wav")
            gen_s = time.time() - t1
            dur = len(audio) / float(sr)
            rec.update(status="ok", total_s=round(gen_s, 2), ttfb_s=None, first_segment_s=round(first or gen_s, 2),
                       audio_s=round(dur, 2), rtf=round(gen_s / dur, 2) if dur else None,
                       peak_gb=round(mx.get_peak_memory() / 1e9, 2), file=os.path.relpath(path, HERE))
        except Exception as e:  # noqa: BLE001
            rec.update(status="failed", error=repr(e)[:400], total_s=round(time.time() - t1, 2))
        log(rec)
        print("%-32s %-3s %-7s gen=%ss audio=%ss rtf=%s peak=%sGB %s" % (
            cfg["key"], pid, rec["status"], rec.get("total_s"), rec.get("audio_s"), rec.get("rtf"),
            rec.get("peak_gb"), rec.get("error", "")[:120]), flush=True)


if __name__ == "__main__":
    main()

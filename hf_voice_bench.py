"""Open-weights voice models via their free Hugging Face demos (Gradio HTTP API). No key, no account, no cost.

  python3 hf_voice_bench.py              # all Spaces, round-robin so each model gets its top line first
  python3 hf_voice_bench.py --only voxcpm2

Every open model clones the same synthetic reference (out-voice/_reference/dadi.wav, made by clone_bench.py),
so voice consistency and cloning are tested together. Anonymous ZeroGPU gives ~2 GPU-minutes a day per IP;
when the quota runs out the ZeroGPU Spaces are skipped cleanly — re-run tomorrow to fill gaps.
Existing outputs are never regenerated.
"""
import argparse
import io
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
import uuid

from voice_bench import HERE, OUT, PROMPTS, log

REF = os.path.join(OUT, "_reference", "dadi.wav")
REF_TEXT = PROMPTS["clone"]["reference_text"]
P = {p["id"]: p for p in PROMPTS["prompts"]}
for c in PROMPTS["clone"]["tests"]:
    P[c["id"]] = {"id": c["id"], "text": c["text"], "emotion": c.get("emotion", "calm, reflective")}
ORDER = ["C1", "C2", "V3", "V6", "V2"]  # clone models: calm, angry, whisper, numbers, Hinglish
# preset-voice models (no cloning) run the V lines; female-only voices get the female versions (C1/C2)
PRESET_ORDER_MALE = ["V1", "V4", "V5", "V3", "V6", "V2", "V7", "V8"]
PRESET_ORDER_FEMALE = ["C1", "C2", "V3", "V6", "V2", "V7", "V8"]
SVARA_TAG = {"V4": "<sad> ", "V5": "<anger> ", "V7": "<happy> ", "V3": "<fear> "}
RUMIK_TONE = {"C1": "professional", "C2": "angry", "V3": "sad", "V6": "professional", "V2": "professional",
              "V7": "happy", "V8": "happy"}
RUMIK_TEXT = {"V8": "<laugh> अरे पागल! तुम भी ना… <sigh> चलो, अब सो जाओ। कल बहुत लंबा दिन है।"}
FISH = {"C2": "[angry, shouting] ", "V3": "[whispering] "}


def exag(pid):
    return 0.8 if pid in ("C2",) else 0.5


SPACES = [
    {"key": "hf__chatterbox-multilingual-hi", "label": "Chatterbox Multilingual (Hindi finetune)",
     "sub": "resembleai-chatterbox-multilingual-tts-hi", "fn": "generate_tts_audio", "zerogpu": True,
     "data": lambda pid, t, ref: [t, ref, exag(pid), 0.8, 0, 0.5]},
    {"key": "hf__chatterbox-multilingual-v3", "label": "Chatterbox Multilingual V3",
     "sub": "resembleai-chatterbox-multilingual-tts-v3", "fn": "generate_tts_audio", "zerogpu": True,
     "data": lambda pid, t, ref: [t, ref, "hi", exag(pid), 0.8, 0, 0.5]},
    {"key": "hf__fish-s2-pro", "label": "Fish S2 Pro (open weights)", "sub": "artificialguybr-fish-s2-pro-zero",
     "fn": "tts_inference", "zerogpu": True,
     "data": lambda pid, t, ref: [FISH.get(pid, "") + t, ref, REF_TEXT, 1024, 200, 0.7, 1.2, 0.7]},
    {"key": "hf__higgs-tts-3", "label": "Higgs TTS 3 (4B)", "sub": "multimodalart-higgs-audio-v3-tts",
     "fn": "synthesize", "zerogpu": True,
     "data": lambda pid, t, ref: [t, ref, REF_TEXT, 0.7, 0.95, 50, 2048, 42]},
    {"key": "hf__voxtral-4b-tts", "label": "Voxtral 4B TTS (Mistral)", "sub": "mistralai-voxtral-tts-demo",
     "fn": "gradio_tts_1", "zerogpu": False, "data": lambda pid, t, ref: [t, ref]},
    {"key": "hf__svara-tts-v1", "label": "Svara TTS v1 (Kenpath, India)", "sub": "kenpath-svara-tts",
     "fn": "generate_speech", "zerogpu": True, "preset": "male",
     "data": lambda pid, t, ref: ["Hindi (हिन्दी)", "Male", SVARA_TAG.get(pid, "") + t, 0.7, 0.8, 1.1, 2048]},
    {"key": "hf__rumik-oss-1", "label": "rumik-oss-1 (Rumik, India)", "sub": "rumik-ai-rumik-oss-1",
     "fn": "synthesize", "zerogpu": True, "preset": "female",
     "data": lambda pid, t, ref: [RUMIK_TEXT.get(pid, t), "Ira", RUMIK_TONE.get(pid, "professional"), "Hindi accent",
                                  "steady pace", "Controls", 0.8, 30, 2048, 42]},
    {"key": "hf__voxcpm2", "label": "VoxCPM2", "sub": "openbmb-voxcpm-demo", "fn": "generate", "zerogpu": False,
     "data": lambda pid, t, ref: [t, "" if pid == "C1" else P[pid]["emotion"], ref, True, REF_TEXT, 2.0, False, False]},
]


def base(s):
    return "https://%s.hf.space" % s["sub"]


def upload(s, path):
    b = "----v" + uuid.uuid4().hex
    body = (("--%s\r\nContent-Disposition: form-data; name=\"files\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
             % (b, os.path.basename(path), mimetypes.guess_type(path)[0] or "audio/wav")).encode()
            + open(path, "rb").read() + ("\r\n--%s--\r\n" % b).encode())
    req = urllib.request.Request(base(s) + "/gradio_api/upload", data=body, method="POST",
                                 headers={"Content-Type": "multipart/form-data; boundary=" + b})
    with urllib.request.urlopen(req, timeout=300) as r:
        return {"path": json.load(r)[0], "meta": {"_type": "gradio.FileData"}}


def call(s, data):
    req = urllib.request.Request(base(s) + "/gradio_api/call/" + s["fn"], data=json.dumps({"data": data}).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        eid = json.load(r)["event_id"]
    event = None
    with urllib.request.urlopen(base(s) + "/gradio_api/call/%s/%s" % (s["fn"], eid), timeout=900) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                payload = line.split(":", 1)[1].strip()
                if event == "error":
                    return "error", payload
                if event == "complete":
                    return "ok", json.loads(payload)
    return "no_result", None


def find_audio_url(obj):
    if isinstance(obj, dict):
        u = obj.get("url") or ""
        if u and any(u.lower().split("?")[0].endswith(x) for x in (".wav", ".mp3", ".flac", ".ogg", ".m4a")):
            return u
        for v in obj.values():
            u = find_audio_url(v)
            if u:
                return u
    if isinstance(obj, list):
        for v in obj:
            u = find_audio_url(v)
            if u:
                return u
    return None


def jobs(spaces, have_ref):
    """Round-robin by priority so every model gets its most important line before anyone gets a second."""
    lists = []
    for s in spaces:
        if s.get("preset"):
            order = PRESET_ORDER_MALE if s["preset"] == "male" else PRESET_ORDER_FEMALE
        elif have_ref:
            order = ORDER
        else:
            continue
        lists.append([(s, pid) for pid in order])
    for i in range(max([len(x) for x in lists] or [0])):
        for x in lists:
            if i < len(x):
                yield x[i]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--presets-only", action="store_true", help="skip the cloning models")
    a = ap.parse_args()
    have_ref = os.path.exists(REF) and not a.presets_only
    if not have_ref and not a.presets_only:
        print("No reference voice yet (clone_bench.py makes it) — running preset-voice models only.")
    spaces = [s for s in SPACES if not a.only or a.only in s["key"]]
    gpu_quota_gone = False
    for s, pid in jobs(spaces, have_ref):
        path = os.path.join(OUT, s["key"], pid + ".wav")
        if os.path.exists(path) or (s["zerogpu"] and gpu_quota_gone) or s.get("dead"):
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": s["key"], "prompt": pid, "space": s["sub"],
               "cost_usd": 0}
        t0 = time.time()
        try:
            ref = None if s.get("preset") else upload(s, REF)
            data = s["data"](pid, P[pid]["text"], ref)
            rec["sent"] = [d if not isinstance(d, dict) else "<reference dadi.wav>" for d in data]
            for attempt in range(10):
                try:
                    status, res = call(s, data)
                    break
                except urllib.error.HTTPError as e:
                    body = e.read().decode("utf-8", "replace")
                    if e.code == 503 and attempt < 9:
                        time.sleep(45)
                        continue
                    raise urllib.error.HTTPError(e.url, e.code, e.msg, e.hdrs, io.BytesIO(body.encode()))
            rec["status"] = status
            if status == "ok":
                url = find_audio_url(res)
                if not url:
                    rec.update(status="no_audio", result=str(res)[:300])
                else:
                    with urllib.request.urlopen(url, timeout=300) as r:
                        open(path, "wb").write(r.read())
                    rec["file"] = os.path.relpath(path, HERE)
            else:
                rec["error"] = str(res)[:400]
                low = str(res).lower()
                if "quota" in low or ("gpu" in low and "exceed" in low):
                    gpu_quota_gone = True
                    rec["status"] = "zerogpu_quota"
        except Exception as e:  # noqa: BLE001
            rec.update(status="failed", error=str(e)[:400])
            if "404" in str(e) or "RUNTIME" in str(e):
                s["dead"] = True
        rec["total_s"] = round(time.time() - t0, 1)
        log(rec)
        print("%-34s %-3s %-14s %5.1fs %s" % (s["key"], pid, rec["status"], rec["total_s"], rec.get("error", "")[:90]),
              flush=True)


if __name__ == "__main__":
    main()

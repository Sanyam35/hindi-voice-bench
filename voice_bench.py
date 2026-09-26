"""Voice model bench — the same Hindi lines through closed TTS models (paid, tiny budget).

Usage:
  python3 voice_bench.py --dry-run               # free: plan + estimated cost, no calls
  python3 voice_bench.py --budget 1.50           # spends, stops before the cap is crossed
  python3 voice_bench.py --budget 1.50 --only elevenlabs__eleven_v3

Rules (same as the image bench, 23 Sep 2026):
  - Hard budget cap, checked BEFORE every call. ElevenLabs is also capped in credits.
  - Never regenerates: an output that already exists on disk is skipped.
  - No retries on uncertain (timeout/network) responses; they count as spent.
  - Keys are read at runtime from existing files and never printed or written.
  - Every call is logged to receipts.jsonl: time to first audio byte, total time, est. cost, status.
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out-voice")
RECEIPTS = os.path.join(HERE, "receipts.jsonl")
PROMPTS = json.load(open(os.path.join(HERE, "prompts.json")))
# Env file with ELEVENLABS_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY / VERCEL_AI_GATEWAY_KEY. Override with VOICE_BENCH_ENV.
STUDIO_ENV = os.environ.get("VOICE_BENCH_ENV") or os.path.expanduser("~/Documents/Kahiyo/content/kahiyo-labs/services/studio/.env")
OPENCODE_AUTH = os.path.expanduser("~/.local/share/opencode/auth.json")
COMPANY_ENV = os.environ.get("VOICE_BENCH_ENV2") or os.path.expanduser("~/projects/company-config/.env")
GATEWAY = "https://ai-gateway.vercel.sh"

# ---- how each engine is told the emotion (same words, each engine's documented method) ----
EL_V3_TAG = {"V1": "[calm]", "V2": "[tired]", "V3": "[whispers]", "V4": "[crying]", "V5": "[angry]",
             "V6": "", "V7": "[cheerfully]"}
FISH_TAG = {"V1": "[calm]", "V2": "[tired]", "V3": "[whispering]", "V4": "[crying]", "V5": "[angry, shouting]",
            "V6": "", "V7": "[cheerful]"}

# est_usd: per call, conservative. el_mult: ElevenLabs credits per character.
MODELS = [
    {"key": "elevenlabs__eleven_v3", "label": "ElevenLabs v3", "engine": "elevenlabs", "model": "eleven_v3",
     "voice": "6xalENe4gtaDq8XTGd7G", "kid_voice": "vzov6y10x6nsGNFg883S", "tags": "el_v3", "el_mult": 1.0,
     "note": "Kahiyo's current model; voices = Gajendra (male lead) and Samisha (kids line)"},
    {"key": "elevenlabs__eleven_v3_conversational", "label": "ElevenLabs v3 Conversational", "engine": "elevenlabs",
     "model": "eleven_v3_conversational", "voice": "6xalENe4gtaDq8XTGd7G", "kid_voice": "vzov6y10x6nsGNFg883S",
     "tags": "el_v3", "el_mult": 0.5, "latency_reps": 3},
    {"key": "elevenlabs__eleven_multilingual_v2", "label": "ElevenLabs Multilingual v2", "engine": "elevenlabs",
     "model": "eleven_multilingual_v2", "voice": "6xalENe4gtaDq8XTGd7G", "kid_voice": "vzov6y10x6nsGNFg883S",
     "tags": None, "el_mult": 1.0},
    {"key": "elevenlabs__eleven_flash_v2_5", "label": "ElevenLabs Flash v2.5", "engine": "elevenlabs",
     "model": "eleven_flash_v2_5", "voice": "6xalENe4gtaDq8XTGd7G", "kid_voice": "vzov6y10x6nsGNFg883S",
     "tags": None, "el_mult": 0.5, "lang": "hi", "latency_reps": 3},
    {"key": "openai__gpt-4o-mini-tts", "label": "OpenAI gpt-4o-mini-tts (Dec 2025)", "engine": "openai",
     "model": "gpt-4o-mini-tts-2025-12-15", "voice": "cedar", "kid_voice": "marin", "fallback": "onyx", "kid_fallback": "coral", "est_usd": 0.004,
     "latency_reps": 3},
    {"key": "google__gemini-3.8-flash-tts", "label": "Gemini 3.8 Flash TTS", "engine": "gemini",
     "model": "gemini-3.8-flash-tts", "voice": "Charon", "kid_voice": "Leda", "est_usd": 0.004, "tags": "gemini", "latency_reps": 3},
    {"key": "google__gemini-3.8-flash-lite-tts", "label": "Gemini 3.8 Flash-Lite TTS", "engine": "gemini",
     "model": "gemini-3.8-flash-lite-tts", "voice": "Charon", "kid_voice": "Leda", "est_usd": 0.003, "tags": "gemini", "latency_reps": 3},
    {"key": "fish-audio__s2.1-pro", "label": "Fish Audio S2.1 Pro (gateway)", "engine": "gateway",
     "model": "fish-audio/s2.1-pro", "voice": "0de8162a9e384545a0106046b57488a7",
     "kid_voice": "4d7609058bd34213b1378b29efbde1f1", "tags": "fish", "usd_per_char": 0.000015 * 2.6,  # Fish bills UTF-8 bytes; Devanagari ~2.56 bytes/char
     "note": "community voices 'Narration' (hi, male) and 'Girl hindi' — origin unknown, test only"},
    {"key": "fish-audio__s2-pro", "label": "Fish Audio S2 Pro (gateway; open weights, hosted)", "engine": "gateway",
     "model": "fish-audio/s2-pro", "voice": "0de8162a9e384545a0106046b57488a7",
     "kid_voice": "4d7609058bd34213b1378b29efbde1f1", "tags": "fish", "usd_per_char": 0.000015 * 2.6},
    {"key": "sarvam__bulbul-v3", "label": "Sarvam Bulbul v3 (India)", "engine": "sarvam", "model": "bulbul:v3",
     "voice": "shubh", "kid_voice": "priya", "usd_per_char": 0.000034, "latency_reps": 3},
    {"key": "cartesia__sonic-3.6", "label": "Cartesia Sonic 3.6", "engine": "cartesia", "model": "sonic-3.6",
     "voice": "7e8cb11d-37af-476b-ab8f-25da99b18644", "kid_voice": "a81fccdc-5595-4dfc-ae76-4de6a515b8a2", "tags": "cartesia", "usd_per_char": 0.00005,
     "latency_reps": 3},
    {"key": "inworld__tts-2", "label": "Inworld TTS-2", "engine": "inworld", "model": "inworld-tts-2",
     "voice": "Manoj", "kid_voice": "Meher", "tags": "inworld", "usd_per_char": 0.000025,
     "latency_reps": 3},
    {"key": "inworld__tts-2-flash", "label": "Inworld TTS-2 Flash", "engine": "inworld", "model": "inworld-tts-2-flash",
     "voice": "Manoj", "kid_voice": "Meher", "tags": "inworld_flash", "usd_per_char": 0.000015,
     "latency_reps": 3},
    {"key": "spacexai__grok-tts", "label": "Grok TTS (gateway)", "engine": "gateway", "model": "spacexai/grok-tts",
     "voice": "naksh", "kid_voice": "eve", "fallback": "rex", "tags": "grok", "usd_per_char": 0.000015, "lang": "hi"},
]


def load_env(path):
    env = {}
    if os.path.exists(path):
        for line in open(path):
            m = re.match(r"^([A-Z0-9_]+)=(.*)$", line.strip())
            if m:
                env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return env


def keys():
    env = load_env(STUDIO_ENV)
    gw = None
    if os.path.exists(OPENCODE_AUTH):
        p = json.load(open(OPENCODE_AUTH)).get("vercel") or {}
        gw = p.get("key") or p.get("apiKey") or p.get("value")
    co = load_env(COMPANY_ENV)
    inw = (co.get("INWORLD_API_KEY") or "").strip()
    if inw.lower().startswith("basic "):
        inw = inw[6:].strip()
    return {"elevenlabs": env.get("ELEVENLABS_API_KEY"), "openai": env.get("OPENAI_API_KEY"),
            "gemini": env.get("GEMINI_API_KEY"), "gateway": gw or env.get("VERCEL_AI_GATEWAY_KEY"),
            "sarvam": co.get("SARVAM_API_KEY"), "cartesia": co.get("CARTESIA_API_KEY"), "inworld": inw or None}


SFX_VOCAB = {"el_v3": {"laugh": "[laughs]", "sigh": "[sighs]"}, "fish": {"laugh": "[laughing]", "sigh": "[sigh]"},
             "grok": {"laugh": "[laugh]", "sigh": "[sigh]"}, "gemini": {"laugh": "<laugh>", "sigh": "<sigh>"},
             "cartesia": {"laugh": "[laughter]", "sigh": ""}, "inworld": {"laugh": "[laughing]", "sigh": "[sighing]"},
             "inworld_flash": {"laugh": "[laugh]", "sigh": "[sigh]"}}
# Inworld TTS-2 steering: English instructions in [brackets] (its docs: instructions must be in English)
INWORLD_TAG = {"V1": "[calm, reflective]", "V2": "[tired, conversational]", "V3": "[whispering, scared]",
               "V4": "[crying, voice breaking]", "V5": "[angry, shouting]", "V7": "[cheerful, warm, talking to a child]"}


def prompt_text(model, p):
    """The exact text sent, with the emotion expressed the way this engine documents."""
    t, emo = p["text"], p.get("emotion", "")
    if p.get("tagged") and model.get("tags") in SFX_VOCAB:
        v = SFX_VOCAB[model["tags"]]
        return re.sub(r"\s+", " ", p["tagged"].format(laugh=v["laugh"], sigh=v["sigh"])).strip()
    if model.get("tags") == "el_v3":
        tag = EL_V3_TAG.get(p["id"], "")
        return (tag + " " + t).strip()
    if model.get("tags") == "fish":
        tag = FISH_TAG.get(p["id"], "")
        return (tag + " " + t).strip()
    if model.get("tags") == "inworld" and INWORLD_TAG.get(p["id"]):
        return INWORLD_TAG[p["id"]] + " " + t
    if model.get("tags") == "grok" and p["id"] == "V3":
        return "<whisper>" + t + "</whisper>"
    return t


def instructions(model, p):
    if model["engine"] == "openai" and p.get("emotion"):
        return "Native Hindi speaker from North India. Delivery: %s." % p["emotion"]
    return None


def est_cost(model, text):
    if model["engine"] == "elevenlabs":
        return 0.0, len(text) * model["el_mult"]
    if "usd_per_char" in model:
        return len(text) * model["usd_per_char"], 0
    return model.get("est_usd", 0.005), 0


def out_file(model, pid, rep=1):
    ext = "wav" if model["engine"] == "gemini" else "mp3"
    name = pid if rep == 1 else "%s_r%d" % (pid, rep)
    return os.path.join(OUT, model["key"], name + "." + ext)


def jobs():
    for m in MODELS:
        for p in PROMPTS["prompts"]:
            reps = m.get("latency_reps", 1) if p["id"] == "V7" else 1
            for r in range(1, reps + 1):
                yield m, p, r


# ---------------- engines: each returns (bytes, ttfb_seconds, extra_dict) ----------------

def stream_read(req, timeout=180):
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        first = resp.read(1024)
        ttfb = time.time() - t0
        rest = resp.read()
    return first + rest, ttfb


def call_elevenlabs(k, m, p, text, voice):
    url = "https://api.elevenlabs.io/v1/text-to-speech/%s/stream?output_format=mp3_44100_128" % voice
    body = {"text": text, "model_id": m["model"]}
    if m.get("lang"):
        body["language_code"] = m["lang"]
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": k, "Content-Type": "application/json"})
    try:
        audio, ttfb = stream_read(req)
        return audio, ttfb, {}
    except urllib.error.HTTPError as e:
        if e.code not in (400, 422):
            raise
        req = urllib.request.Request(url.replace("/stream?", "?"), data=json.dumps(body).encode(), method="POST",
                                     headers={"xi-api-key": k, "Content-Type": "application/json"})
        audio, ttfb = stream_read(req)
        return audio, ttfb, {"streamed": False, "stream_error": e.read().decode(errors="ignore")[:200]}


def call_openai(k, m, p, text, voice):
    body = {"model": m["model"], "voice": voice, "input": text, "response_format": "mp3"}
    ins = instructions(m, p)
    if ins:
        body["instructions"] = ins
    req = urllib.request.Request("https://api.openai.com/v1/audio/speech", data=json.dumps(body).encode(),
                                 method="POST", headers={"Authorization": "Bearer " + k,
                                                         "Content-Type": "application/json"})
    audio, ttfb = stream_read(req)
    return audio, ttfb, {"instructions": ins}


def pcm_to_wav(pcm, rate=24000):
    import struct
    hdr = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    return hdr + b"data" + struct.pack("<I", len(pcm)) + pcm


def call_gemini(k, m, p, text, voice, style=None):
    """Gemini 3.8 TTS via the Interactions API (streamed). The text is read verbatim, so the acting
    direction goes in speech_metadata.style, never in the text."""
    style = style if style is not None else p.get("emotion")
    content = {"type": "text", "text": text}
    if style:
        content["annotations"] = [{"type": "speech_metadata", "style": style}]
    body = {"model": m["model"], "input": [{"type": "user_input", "content": [content]}],
            "response_format": {"type": "audio"}, "generation_config": {"speech_config": [{"voice": voice}]},
            "stream": True}
    req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/interactions",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"x-goog-api-key": k, "Content-Type": "application/json"})
    t0 = time.time()
    pcm, wav, ttfb, usage, raw_all = b"", None, None, {}, b""
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw in resp:
            raw_all += raw
            line = raw.decode(errors="ignore").strip()
            if line.startswith("data:"):
                line = line[5:].strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            usage = ev.get("usage") or (ev.get("interaction") or {}).get("usage") or usage
            d = (ev.get("delta") or {}).get("data")
            if d:
                if ttfb is None:
                    ttfb = time.time() - t0
                pcm += base64.b64decode(d)
    if not pcm:  # server answered with one JSON body instead of a stream
        try:
            body = json.loads(raw_all)
            for st in body.get("steps", []):
                for c in st.get("content", []):
                    if c.get("type") == "audio" and c.get("data"):
                        wav = base64.b64decode(c["data"])
            usage = body.get("usage", usage)
            ttfb = time.time() - t0
        except ValueError:
            pass
        if wav:
            return wav, ttfb, {"style": style, "usage": usage, "streamed": False}
    if not pcm:
        raise RuntimeError("no audio in Gemini response")
    return pcm_to_wav(pcm), ttfb, {"style": style, "usage": usage}


def call_gateway(k, m, p, text, voice):
    body = {"text": text, "voice": voice, "outputFormat": "mp3"}
    if m.get("lang"):
        body["language"] = m["lang"]
    req = urllib.request.Request(GATEWAY + "/v4/ai/speech-model", data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + k, "ai-gateway-protocol-version": "0.0.1",
                                          "ai-speech-model-specification-version": "4", "ai-model-id": m["model"],
                                          "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        res = json.load(resp)
    return base64.b64decode(res["audio"]), time.time() - t0, {"warnings": res.get("warnings"), "streaming": False}


def call_sarvam(k, m, p, text, voice):
    body = {"text": text, "language_code": "hi-IN", "speaker": voice, "model": m["model"],
            "speech_sample_rate": 24000, "output_audio_codec": "mp3"}
    req = urllib.request.Request("https://api.sarvam.ai/text-to-speech", data=json.dumps(body).encode(), method="POST",
                                 headers={"api-subscription-key": k, "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        res = json.load(resp)
    return b"".join(base64.b64decode(a) for a in res["audios"]), time.time() - t0, {"streaming": False}


CARTESIA_VERSION = "2026-08-14"


def call_cartesia(k, m, p, text, voice):
    body = {"model_id": m["model"], "transcript": text, "voice": {"mode": "id", "id": voice}, "language": "hi",
            "output_format": {"container": "mp3", "sample_rate": 44100, "bit_rate": 128000}}
    req = urllib.request.Request("https://api.cartesia.ai/tts/bytes", data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + k, "Cartesia-Version": CARTESIA_VERSION,
                                          "Content-Type": "application/json"})
    audio, ttfb = stream_read(req)
    return audio, ttfb, {}


def call_inworld(k, m, p, text, voice):
    body = {"text": text, "voiceId": voice, "modelId": m["model"], "language": "hi-IN",
            "audioConfig": {"audioEncoding": "MP3"}}
    req = urllib.request.Request("https://api.inworld.ai/tts/v1/voice:stream", data=json.dumps(body).encode(),
                                 method="POST", headers={"Authorization": "Basic " + k,
                                                         "Content-Type": "application/json"})
    t0 = time.time()
    audio, ttfb = b"", None
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw in resp:
            line = raw.decode(errors="ignore").strip()
            if line.startswith("data:"):
                line = line[5:].strip()
            if not line.startswith("{"):
                continue
            ev = json.loads(line)
            chunk = (ev.get("result") or ev).get("audioContent")
            if chunk:
                if ttfb is None:
                    ttfb = time.time() - t0
                audio += base64.b64decode(chunk)
    if not audio:
        raise RuntimeError("no audio in Inworld stream")
    return audio, ttfb, {}


ENGINES = {"sarvam": call_sarvam, "cartesia": call_cartesia, "inworld": call_inworld, "elevenlabs": call_elevenlabs, "openai": call_openai, "gemini": call_gemini, "gateway": call_gateway}


def gateway_balance(k):
    try:
        req = urllib.request.Request(GATEWAY + "/v1/credits", headers={"Authorization": "Bearer " + k})
        return json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:120]}


def el_balance(k):
    try:
        req = urllib.request.Request("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": k})
        s = json.load(urllib.request.urlopen(req, timeout=30))
        return {"used": s["character_count"], "limit": s["character_limit"],
                "left": s["character_limit"] - s["character_count"]}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:120]}


def log(rec):
    with open(RECEIPTS, "a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=0.0, help="USD cap for OpenAI + Gemini + gateway")
    ap.add_argument("--el-credits", type=int, default=15000, help="ElevenLabs credit cap")
    ap.add_argument("--only", default="", help="comma-separated model keys")
    a = ap.parse_args()
    only = set(filter(None, a.only.split(",")))

    todo, usd, cr, skipped = [], 0.0, 0.0, 0
    for m, p, r in jobs():
        if only and m["key"] not in only:
            continue
        if os.path.exists(out_file(m, p["id"], r)):
            skipped += 1
            continue
        c_usd, c_cr = est_cost(m, prompt_text(m, p))
        todo.append((m, p, r, c_usd, c_cr))
        usd += c_usd
        cr += c_cr
    print("Plan: %d calls (%d already on disk, skipped). Estimated: $%.3f + %d ElevenLabs credits." % (
        len(todo), skipped, usd, cr))
    by = {}
    for m, p, r, c_usd, c_cr in todo:
        b = by.setdefault(m["label"], [0, 0.0, 0])
        b[0] += 1; b[1] += c_usd; b[2] += c_cr
    for lab, (n, u, c) in by.items():
        print("  %-38s %2d calls  $%.4f  %5d credits" % (lab, n, u, c))
    if a.dry_run:
        return

    K = keys()
    for eng in {m["engine"] for m, *_ in todo}:
        if not K.get(eng):
            sys.exit("BLOCKER: no key for %s" % eng)
    if K.get("gateway"):
        print("Gateway balance before:", json.dumps(gateway_balance(K["gateway"])))
    if K.get("elevenlabs"):
        print("ElevenLabs credits before:", json.dumps(el_balance(K["elevenlabs"])))

    spent_usd, spent_cr = 0.0, 0.0
    for m, p, r, c_usd, c_cr in todo:
        if spent_usd + c_usd > a.budget + 1e-9 or spent_cr + c_cr > a.el_credits:
            print("STOP: next call would cross the cap ($%.3f / %d credits spent)." % (spent_usd, spent_cr))
            break
        text = prompt_text(m, p)
        voice = m["kid_voice"] if p["id"] == "V7" else m["voice"]
        path = out_file(m, p["id"], r)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": m["key"], "prompt": p["id"], "rep": r,
               "voice": voice, "sent_text": text, "est_usd": c_usd, "est_credits": c_cr}
        t0 = time.time()
        try:
            try:
                audio, ttfb, extra = ENGINES[m["engine"]](K[m["engine"]], m, p, text, voice)
            except urllib.error.HTTPError as e:
                fb = m.get("kid_fallback" if p["id"] == "V7" else "fallback")
                if e.code not in (400, 404, 422) or not fb:
                    raise
                rec["first_try"] = "http_%d %s" % (e.code, e.read().decode(errors="ignore")[:200])
                voice = rec["voice"] = fb
                t0 = time.time()
                audio, ttfb, extra = ENGINES[m["engine"]](K[m["engine"]], m, p, text, voice)
            with open(path, "wb") as fh:
                fh.write(audio)
            rec.update(status="ok", ttfb_s=round(ttfb, 3) if ttfb else None, total_s=round(time.time() - t0, 3),
                       bytes=len(audio), file=os.path.relpath(path, HERE), **extra)
        except urllib.error.HTTPError as e:
            rec.update(status="http_%d" % e.code, error=e.read().decode(errors="ignore")[:400],
                       total_s=round(time.time() - t0, 3))
            c_usd, c_cr = 0.0, 0.0  # provider rejected: not billed
        except Exception as e:  # noqa: BLE001  uncertain: count as spent, never retry
            rec.update(status="uncertain", error=str(e)[:300], total_s=round(time.time() - t0, 3))
        spent_usd += c_usd
        spent_cr += c_cr
        log(rec)
        print("%-36s %-3s r%d %-10s ttfb=%s total=%.1fs" % (m["key"], p["id"], r, rec["status"],
                                                          rec.get("ttfb_s"), rec["total_s"]))
    print("Spent (est.): $%.3f + %d ElevenLabs credits." % (spent_usd, spent_cr))
    if K.get("gateway"):
        print("Gateway balance after:", json.dumps(gateway_balance(K["gateway"])))
    if K.get("elevenlabs"):
        print("ElevenLabs credits after:", json.dumps(el_balance(K["elevenlabs"])))


if __name__ == "__main__":
    main()

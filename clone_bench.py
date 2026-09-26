"""Cloning + speech-to-speech (voice changer) tests on closed models. Synthetic voices only.

  python3 clone_bench.py --dry-run
  python3 clone_bench.py --budget 0.05 --el-credits 3000

Steps (each skipped if its output already exists):
  R  make the reference: 'Dadi' (elderly woman) spoken by Gemini 3.8 Flash TTS — a synthetic voice,
     not a real person. Saved to out-voice/_reference/dadi.wav (+ a 16 kHz mp3 copy for uploads).
  C  ElevenLabs Instant Voice Clone from that clip -> speak C1 (calm) and C2 (angry) with eleven_v3,
     then DELETE the temporary clone from the account (Kahiyo production rule: no cloned voices kept).
  S  ElevenLabs speech-to-speech: take OpenAI's angry take (V5) and re-voice it as Gajendra, the Kahiyo lead.
"""
import argparse
import json
import os
import subprocess
import time
import urllib.request
import uuid

from voice_bench import HERE, OUT, PROMPTS, call_gemini, keys, log

REF_DIR = os.path.join(OUT, "_reference")
REF_WAV = os.path.join(REF_DIR, "dadi.wav")
REF_MP3 = os.path.join(REF_DIR, "dadi.mp3")
EL_CLONE_DIR = os.path.join(OUT, "elevenlabs__ivc-clone")
EL_STS_DIR = os.path.join(OUT, "elevenlabs__sts-multilingual-v2")
GAJENDRA = "6xalENe4gtaDq8XTGd7G"
STS_SOURCE = os.path.join(OUT, "openai__gpt-4o-mini-tts", "V5.mp3")


def multipart(fields, files):
    b = uuid.uuid4().hex
    out = []
    for k, v in fields:
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b, k, v)).encode())
    for k, name, data, ctype in files:
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
                    % (b, k, name, ctype)).encode() + data + b"\r\n")
    out.append(("--%s--\r\n" % b).encode())
    return b"".join(out), "multipart/form-data; boundary=" + b


def el(key, method, path, body=None, ctype="application/json", stream=False):
    req = urllib.request.Request("https://api.elevenlabs.io" + path, data=body, method=method,
                                 headers={"xi-api-key": key, "Content-Type": ctype})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        if stream:
            first = resp.read(1024)
            ttfb = time.time() - t0
            return first + resp.read(), ttfb
        return json.load(resp), time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=0.0)
    ap.add_argument("--el-credits", type=int, default=3000)
    a = ap.parse_args()
    ref_text = PROMPTS["clone"]["reference_text"]
    tests = PROMPTS["clone"]["tests"]
    need_ref = not os.path.exists(REF_WAV)
    need_clone = [t for t in tests if not os.path.exists(os.path.join(EL_CLONE_DIR, t["id"] + ".mp3"))]
    need_sts = not os.path.exists(os.path.join(EL_STS_DIR, "S1.mp3"))
    credits = sum(len(t["text"]) + 10 for t in need_clone) + (1000 if need_sts else 0)
    print("Plan: reference=%s ($0.004), clone lines=%d, speech-to-speech=%s. Est. $%.3f + ~%d ElevenLabs credits."
          % (need_ref, len(need_clone), need_sts, 0.004 if need_ref else 0, credits))
    if a.dry_run:
        return
    if credits > a.el_credits or (need_ref and a.budget < 0.004):
        raise SystemExit("STOP: over the cap.")
    K = keys()
    os.makedirs(REF_DIR, exist_ok=True)

    if need_ref:
        text = ref_text
        audio, ttfb, extra = call_gemini(K["gemini"], {"model": "gemini-3.8-flash-tts"}, {}, text, "Sulafat",
                                         style="a 70-year-old grandmother from Lucknow: slow, warm, a slight "
                                               "tremble, very tender")
        open(REF_WAV, "wb").write(audio)
        log({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": "google__gemini-3.8-flash-tts", "prompt": "REF",
             "status": "ok", "ttfb_s": ttfb, "file": os.path.relpath(REF_WAV, HERE), "sent_text": text, **extra})
    if not os.path.exists(REF_MP3):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", REF_WAV, "-ac", "1", "-b:a", "128k", REF_MP3], check=True)

    if need_clone:
        os.makedirs(EL_CLONE_DIR, exist_ok=True)
        body, ctype = multipart([("name", "BENCH-TEMP dadi synthetic (delete me)"),
                                 ("description", "Temporary voice-bench clone of a synthetic Gemini voice")],
                                [("files", "dadi.mp3", open(REF_MP3, "rb").read(), "audio/mpeg")])
        res, _ = el(K["elevenlabs"], "POST", "/v1/voices/add", body, ctype)
        vid = res["voice_id"]
        try:
            for t in need_clone:
                txt = ("[angry] " if t.get("emotion") else "") + t["text"]
                path = os.path.join(EL_CLONE_DIR, t["id"] + ".mp3")
                rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": "elevenlabs__ivc-clone", "prompt": t["id"],
                       "sent_text": txt, "voice": "temporary IVC of dadi.mp3"}
                t0 = time.time()
                try:
                    audio, ttfb = el(K["elevenlabs"], "POST",
                                     "/v1/text-to-speech/%s/stream?output_format=mp3_44100_128" % vid,
                                     json.dumps({"text": txt, "model_id": "eleven_v3"}).encode(), stream=True)
                    open(path, "wb").write(audio)
                    rec.update(status="ok", ttfb_s=round(ttfb, 3), total_s=round(time.time() - t0, 3),
                               file=os.path.relpath(path, HERE))
                except Exception as e:  # noqa: BLE001
                    rec.update(status="error", error=str(e)[:300])
                log(rec)
                print(rec["prompt"], rec["status"], rec.get("ttfb_s"))
        finally:
            el(K["elevenlabs"], "DELETE", "/v1/voices/%s" % vid)
            print("Temporary clone deleted from the ElevenLabs account.")

    if need_sts:
        if not os.path.exists(STS_SOURCE):
            print("Skip speech-to-speech: run voice_bench.py first (needs %s)." % STS_SOURCE)
            return
        os.makedirs(EL_STS_DIR, exist_ok=True)
        body, ctype = multipart([("model_id", "eleven_multilingual_sts_v2")],
                                [("audio", "v5.mp3", open(STS_SOURCE, "rb").read(), "audio/mpeg")])
        t0 = time.time()
        audio, ttfb = el(K["elevenlabs"], "POST", "/v1/speech-to-speech/%s/stream?output_format=mp3_44100_128"
                         % GAJENDRA, body, ctype, stream=True)
        path = os.path.join(EL_STS_DIR, "S1.mp3")
        open(path, "wb").write(audio)
        log({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": "elevenlabs__sts-multilingual-v2", "prompt": "S1",
             "status": "ok", "ttfb_s": round(ttfb, 3), "total_s": round(time.time() - t0, 3),
             "source": os.path.relpath(STS_SOURCE, HERE), "voice": GAJENDRA, "file": os.path.relpath(path, HERE)})
        print("S1 ok", round(ttfb, 2))


if __name__ == "__main__":
    main()

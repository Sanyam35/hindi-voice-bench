"""Build the Voice Model Lab page data: ../voice-page/data.json + small mp3 copies of every clip.

  python3 build_page.py        # free, local only; safe to re-run after every bench run
"""
import glob
import json
import os
import statistics
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out-voice")
PAGE = os.path.join(os.path.dirname(HERE), "voice-page")
AUDIO = os.path.join(PAGE, "audio")


def jl(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


METRICS = [
    {"id": "clarity", "name": "Hindi clarity", "what": "Did it say every word? Skips, mumbles, invented words.",
     "how": "Transcribe the clip back to text (OpenAI gpt-4o-transcribe, Hindi) and count character errors (CER) against the script, ignoring nukta and ँ/ं spelling.",
     "bar": "Hindi speech-to-text itself makes ~8–10% errors on clean human speech, so compare models with each other, not to zero.", "use": "Both", "status": "auto"},
    {"id": "checklist", "name": "Line checklist", "what": "The planted details: nuktas (ज़), lakh numbering, dates, names, tags not read aloud.",
     "how": "An AI listener (Gemini 3.1 Pro, hears the audio) ticks each line's checklist.", "bar": "Count of ticks; every miss is listed with a quote.", "use": "Both", "status": "auto"},
    {"id": "naturalness", "name": "Naturalness", "what": "Does it sound like a native Hindi actor, not a machine?",
     "how": "AI listener 1–5, then your blind A/B votes decide.", "bar": "English-trained auto-scorers (UTMOS) can't rank Hindi — only human votes count as final.", "use": "Both", "status": "ai+human"},
    {"id": "emotion", "name": "Acting", "what": "Whisper, crying, anger — from the direction, not the words.",
     "how": "AI listener 1–5 on V3–V5, plus loudness change vs the calm line (a whisper should be quieter, anger louder).",
     "bar": "Emotion accuracy drops sharply when the words don't signal the emotion (CosyVoice 3: sad 0.64 → 0.44).", "use": "Drama", "status": "auto"},
    {"id": "sfx", "name": "Sound effects", "what": "A laugh and a sigh on cue (V8) without speaking the tags.",
     "how": "AI listener checklist on V8.", "bar": "Good ≥ 90% cues present and natural (our bar; no published one).", "use": "Drama", "status": "auto"},
    {"id": "consistency", "name": "Voice consistency", "what": "Same character across calm, crying and angry lines.",
     "how": "AI listener hears 3 clips together and rates 'same person' 1–5. (Speaker-embedding similarity needs a local model — added when the Mac install is approved.)",
     "bar": "Human-vs-human similarity ≈ 0.73–0.75 on speaker embeddings (Seed-TTS-Eval).", "use": "Drama", "status": "auto"},
    {"id": "clone", "name": "Cloning likeness", "what": "Does the clone sound like the reference voice?",
     "how": "Every clone speaks C1/C2 from the same synthetic 'Dadi' clip; AI listener rates similarity 1–5.", "bar": "Good ≥ 4/5.", "use": "Drama", "status": "auto"},
    {"id": "phone", "name": "Phone-line clarity", "what": "Still clear after an 8 kHz μ-law phone line (how Retell/Twilio calls sound).",
     "how": "Convert the calm line to 8 kHz μ-law, transcribe again, compare CER.", "bar": "Good = error rate rises by < 1 point.", "use": "Bot", "status": "auto"},
    {"id": "ttfa", "name": "Time to first audio", "what": "How long before the first sound arrives.",
     "how": "Streaming APIs, measured from India, median of 3 runs of the kids line (V7). Gateway can't stream, so its number is the full clip time.",
     "bar": "Voice's share of a turn: good ≤ 150 ms, ok ≤ 250 ms (Vapi, Hamming). Humans reply in ~200 ms. Our numbers include India→US network.", "use": "Bot", "status": "auto"},
    {"id": "cost", "name": "Cost per minute", "what": "Price for one spoken minute of Hindi.",
     "how": "Vendor price pages, ~900 characters per minute. Fish bills bytes: Hindi costs ~2.5× its headline.", "bar": "Lower is better; watch Gemini's 1 Jan 2027 price doubling.", "use": "Both", "status": "desk"},
    {"id": "licence", "name": "Licence", "what": "Can we use it commercially?",
     "how": "Read the actual LICENSE file, not the README badge.", "bar": "Most 'open' voice models are research-only.", "use": "Both", "status": "desk"},
    {"id": "longform", "name": "Long-episode stability", "what": "Skips and made-up words over a 1,500-word episode.",
     "how": "Not run yet — needs a long script × 3 seeds. Proposed for round 2.", "bar": "Qwen3-TTS worst-seed errors went 5% → 35% past 1,500 words.", "use": "Drama", "status": "next"},
    {"id": "e2e", "name": "Whole-call latency", "what": "User stops talking → bot starts talking.",
     "how": "A Retell platform number (turn detection, LLM, voice). Needs a test agent on Retell — round 2, with your OK.", "bar": "Vapi: p50 < 500 ms, p95 < 800 ms.", "use": "Bot", "status": "next"},
    {"id": "kidrate", "name": "Kid-friendly pace", "what": "Slow enough for a 6-year-old.",
     "how": "Syllables per second on V7 (from duration).", "bar": "Children understood more at 2.6–3.4 syllables/sec than at 4.7–6.3 (1973 study).", "use": "Bot", "status": "auto"},
]


# Plain-English findings. Each carries its proof (file, number or source). Edited by hand after every run.
FINDINGS = [
    {"k": "verdict", "t": "Kahiyo drama: Gemini 3.8 Flash-Lite TTS leads this test, at a tenth of ElevenLabs v3's price.",
     "p": "AI listener: natural 4.75/5, acting 4.67/5, 95% of checklist items. Measured: whisper 10.3 dB quieter and anger 7.3 dB louder than the calm line; laugh + sigh on cue. $0.009/min vs $0.09 for ElevenLabs v3. Caveat: the AI listener is also Google's — confirm with your blind votes."},
    {"k": "verdict", "t": "ElevenLabs v3 (Kahiyo's current model) does act, but the AI listener found it the least natural of the paid leaders.",
     "p": "Measured: whisper −4.4 dB, anger +5.9 dB (real changes). AI listener: natural 3.4/5, acting 1.3/5 ('flat', 'robotic' on V4), kids' line 3/5. Costs the most at $0.09/min. Where loudness and the AI disagree, your ears decide."},
    {"k": "verdict", "t": "MyWonder on Retell: Cartesia Sonic 3.6 is the best fit — fast, clear, perfect numbers, warm kids' line.",
     "p": "First sound 0.48 s from India (median of 3), natural 4.25/5, numbers checklist 100%, kids' line 5/5, on Retell at +$0.015/min. Weak at acting (whisper +0.5 dB) — Cartesia's emotion control is English-only — which matters little for a bot."},
    {"k": "verdict", "t": "Runners-up for the bot: ElevenLabs v3 Conversational and Inworld TTS-2.",
     "p": "v3 Conversational: 0.56 s, kids' line 5/5, real acting (−6.3 / +8.0 dB) — but Retell doesn't offer it. Inworld TTS-2: on Retell, kids' line 5/5, Hinglish 5/5, 1.38 s, $0.0225/min. ElevenLabs Flash v2.5 is fastest (0.34 s) but its kids' line scored 2/5."},
    {"k": "verdict", "t": "Open-source is not yet close for Hindi on a 16 GB Mac. VoxCPM2 is the one to watch.",
     "p": "On the Mac: VoxCPM2 natural 4.0/5 but 8× slower than real time (9 GB peak); Chatterbox 2.75/5; rumik 3.0/5; Kokoro 1.4/5 (fast but robotic Hindi). VoxCPM2's full-size online demo scored 4.67/5 on 3 clips — it needs a GPU server, not a laptop."},
    {"k": "verdict", "t": "Sarvam (India) is best at numbers and calm narration, but it can't act and stumbles on romanised Hinglish.",
     "p": "Numbers checklist 100%, calm narration 5/5; whisper +1.2 dB (no change), acting 1/5; kids' line with 'Chalo' 1/5 — Sarvam's own docs warn 'Romanised Indic input degrades quality'. No streaming (2.8 s)."},
    {"k": "run", "t": "Cloning from a 12-second clip was weak everywhere.",
     "p": "AI listener 'sounds like the reference' ≈ 1–1.5/5 for ElevenLabs instant clone, Chatterbox and VoxCPM2 on the Mac ('sounds younger, lacks the aged quality'). ElevenLabs recommends 1–2 minutes of audio; a longer reference is round 2."},
    {"k": "run", "t": "The phone line didn't hurt anyone: every model stayed just as clear at 8 kHz.",
     "p": "Transcript error rate after 8 kHz μ-law conversion rose by at most 1 point for every model checked (extra_scores.jsonl)."},
    {"k": "run", "t": "Fastest first sound from India: ElevenLabs Flash v2.5 (0.34 s), Cartesia (0.48 s), ElevenLabs v3 Conversational (0.56 s).",
     "p": "Median of 3 runs of the kids' line. Gemini 2.3–2.8 s and OpenAI 1.8 s are too slow for a live bot; Sarvam, Grok and Fish can't stream."},
    {"k": "research", "t": "Two measuring traps we caught and corrected.",
     "p": "(1) The transcriber wrote 11 clips' Hindi in Urdu script, which looked like 100% errors — excluded, not counted against the model. (2) The AI listener and the loudness meter disagree on ElevenLabs acting — so both are shown, and your blind votes are final."},
    {"k": "research", "t": "Public voice leaderboards don't test Hindi.",
     "p": "HF TTS Arena docs: 'Prompts are English-only for now'. Cartesia ranks #1 on Artificial Analysis and did well here; ElevenLabs v3 ranks #17 there."},
    {"k": "research", "t": "Fish bills bytes (Hindi ≈ 2.5× its headline); Gemini's price doubles on 1 Jan 2027; Sarvam has no open model.",
     "p": "fish.audio pricing '$15 per 1M bytes'; ai.google.dev pricing; huggingface.co/sarvamai has no text-to-speech repo."},
]

NEEDS = [
    {"t": "Run the paid part", "d": "Done 26 Sep — gateway $97.369 → $97.296 ($0.07), ElevenLabs 1,934 credits, Sarvam/Cartesia/Inworld on free credits.", "state": "done"},
    {"t": "OK to install open models on your Mac", "d": "Done — Kokoro, Chatterbox V3, VoxCPM2, rumik (4.7 GB + 3.2 GB) in ~/projects/model-lab/models/voice.", "state": "done"},
    {"t": "Signups: Sarvam, Cartesia, Inworld", "d": "Done — all three keys work and are in the test.", "state": "done"},
    {"t": "10 minutes of your ears", "d": "The Blind test tab. AI listeners can't be trusted on Hindi — your votes are the final word.", "state": "open"},
    {"t": "Free Hugging Face token (optional)", "d": "Unlocks the 3 models the free demos blocked today (Higgs 3, Voxtral, Chatterbox Hindi). Or wait a day for the limit to reset.", "state": "optional"},
    {"t": "Where to open-source it", "d": "Which GitHub account, and whose name on the MIT licence.", "state": "open"},
]


def script_ok(t):
    """gpt-4o-transcribe sometimes writes heard Hindi in Urdu (Perso-Arabic) script; CER is meaningless then."""
    if not t:
        return True
    arabic = sum(1 for ch in t if "\u0600" <= ch <= "\u06ff")
    letters = sum(1 for ch in t if ch.isalpha())
    return arabic < 0.3 * max(1, letters)


def to_mp3(src, dst):
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "24000", "-b:a", "64k", dst], check=True)


def main():
    prompts = json.load(open(os.path.join(HERE, "prompts.json")))
    catalog = json.load(open(os.path.join(HERE, "catalog.json")))
    receipts = jl(os.path.join(HERE, "receipts.jsonl"))
    scores = {(s["model"], s["prompt"]): s for s in jl(os.path.join(HERE, "scores.jsonl"))}
    extras = {e["model"]: e for e in jl(os.path.join(HERE, "extra_scores.jsonl"))}
    last = {}
    for r in receipts:
        last[(r["model"], r["prompt"], r.get("rep", 1))] = r

    clips = []
    for f in sorted(glob.glob(os.path.join(OUT, "*", "*.*"))):
        model = os.path.basename(os.path.dirname(f))
        if model.startswith("_"):
            continue
        name = os.path.splitext(os.path.basename(f))[0]
        pid, rep = (name.split("_r")[0], int(name.split("_r")[1])) if "_r" in name else (name, 1)
        rel = "audio/%s/%s.mp3" % (model, name)
        to_mp3(f, os.path.join(PAGE, rel))
        r = last.get((model, pid, rep), {})
        s = scores.get((model, pid), {}) if rep == 1 else {}
        clips.append({"model": model, "prompt": pid, "rep": rep, "url": rel,
                      "ttfb": r.get("ttfb_s"), "total": r.get("total_s"), "voice": r.get("voice"),
                      "sent": r.get("sent_text") or r.get("sent"), "style": r.get("style") or r.get("instructions"),
                      "streamed": not (r.get("streamed") is False or r.get("streaming") is False
                                       or model.startswith(("fish-audio__", "spacexai__", "hf__", "mac__"))),
                      "rtf": r.get("rtf"), "peak_gb": r.get("peak_gb"), "load_s": r.get("load_s"),
                      "duration": s.get("duration_s"), "lufs": s.get("lufs"),
                      "cer": s.get("cer") if script_ok(s.get("transcript")) else None,
                      "urdu_script": not script_ok(s.get("transcript")),
                      "transcript": s.get("transcript"), "judge": s.get("judge")})
    ref = os.path.join(OUT, "_reference", "dadi.wav")
    ref_url = None
    if os.path.exists(ref):
        ref_url = "audio/_reference/dadi.mp3"
        to_mp3(ref, os.path.join(PAGE, ref_url))

    # per-model latency: median over V7 runs (streaming engines only)
    lat, whole = {}, {}
    for c in clips:
        if c["prompt"] != "V7" or c["model"].startswith("mac__"):
            continue
        if c["streamed"] and c["ttfb"]:
            lat.setdefault(c["model"], []).append(c["ttfb"])
        elif c["total"]:
            whole.setdefault(c["model"], []).append(c["total"])
    latency = {m: {"median": round(statistics.median(v), 3), "n": len(v), "all": v, "streamed": True}
               for m, v in lat.items()}
    for m, v in whole.items():
        latency.setdefault(m, {"median": round(statistics.median(v), 3), "n": len(v), "all": v, "streamed": False})
    acting = {}
    for m in {c["model"] for c in clips}:
        L = {c["prompt"]: c["lufs"] for c in clips if c["model"] == m and c["rep"] == 1 and c.get("lufs") is not None}
        calm = L.get("V1", L.get("C1"))
        if calm is not None:
            acting[m] = {"whisper_db": round(L["V3"] - calm, 1) if "V3" in L else None,
                         "anger_db": round(L["V5"] - calm, 1) if "V5" in L else
                         (round(L["C2"] - L["C1"], 1) if "C2" in L and "C1" in L else None)}
    for m, e in extras.items():
        ph = e.get("phone") or {}
        if ph and not script_ok(ph.get("transcript")):
            ph["cer"] = None
            ph["urdu_script"] = True
    mac = {}
    for c in clips:
        if c["model"].startswith("mac__") and c.get("rtf"):
            mac.setdefault(c["model"], {"rtf": [], "peak": [], "load": c.get("load_s")})
            mac[c["model"]]["rtf"].append(c["rtf"])
            mac[c["model"]]["peak"].append(c.get("peak_gb") or 0)
    mac = {m: {"rtf": round(statistics.median(v["rtf"]), 2), "peak_gb": max(v["peak"]), "load_s": v["load"],
               "n": len(v["rtf"])} for m, v in mac.items()}

    fails = [{"model": r["model"], "prompt": r["prompt"], "status": r["status"], "error": (r.get("error") or "")[:160]}
             for r in receipts if r.get("status") not in ("ok",)]
    spend = round(sum(r.get("est_usd") or 0 for r in receipts if r.get("status") in ("ok", "uncertain")), 3)
    credits = int(sum(r.get("est_credits") or 0 for r in receipts if r.get("status") in ("ok", "uncertain")))

    data = {"built": time.strftime("%d %b %Y, %H:%M"), "prompts": prompts, "catalog": catalog, "metrics": METRICS,
            "clips": clips, "extras": extras, "latency": latency, "mac": mac, "acting": acting, "reference": ref_url, "failures": fails,
            "spend_usd_est": spend, "el_credits_est": credits,
            "findings": FINDINGS, "needs": NEEDS}
    os.makedirs(PAGE, exist_ok=True)
    json.dump(data, open(os.path.join(PAGE, "data.json"), "w"), ensure_ascii=False, indent=0)
    print("clips=%d models_with_audio=%d failures=%d spend≈$%.3f credits≈%d -> %s" % (
        len(clips), len({c["model"] for c in clips}), len(fails), spend, credits, PAGE))


if __name__ == "__main__":
    main()

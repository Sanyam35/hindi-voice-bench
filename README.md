# Hindi Voice Bench

A small, honest benchmark for **Hindi and Hinglish text-to-speech**, built for first-person audio dramas and a kids' voice bot.
Public leaderboards test English only ("Prompts are English-only for now" — TTS Arena docs), so this bench tests what Hindi
productions actually need.

## What it tests
Eight fixed lines (`prompts.json`), each with a checklist:
calm narration · Hinglish · whisper · crying · anger · numbers/dates/names (lakh, ₹, phone digits) · a kids' line · laugh + sigh.
Plus cloning from a **synthetic** reference voice, a voice changer, and an 8 kHz phone-line check.

Each model is scored on separate measures — never one number:
Hindi clarity (round-trip transcript error rate) · checklist ticks · naturalness · acting · sound effects · same-voice consistency ·
clone likeness · phone-line clarity · time to first audio · kid pace · cost per minute · licence · **blind human votes**.
AI listeners are a first pass only; English-trained auto-scorers can't rank Hindi, so human blind votes decide.

## Models covered
Closed: ElevenLabs (v3, v3 Conversational, Multilingual v2, Flash v2.5), OpenAI gpt-4o-mini-tts, Gemini 3.8 Flash / Flash-Lite TTS,
Fish S2.1 Pro and Grok TTS (via Vercel AI Gateway). Open: Chatterbox (+ Hindi finetune), VoxCPM2, Fish S2 Pro, Higgs TTS 3,
Voxtral, and Indian models Svara and rumik-oss-1 — via free Hugging Face demos. `catalog.json` maps 29 options (incl. Sarvam, Cartesia, Inworld, Smallest, MiniMax, Azure) with price,
licence (read from the actual LICENSE file) and sources.

## Round 1 results (26 Sep 2026, 170 clips, 22 models)
First pass only: an AI listener (Gemini 3.1 Pro) plus plain measurements. The AI listener is Google's, so it may favour
Google voices, and it is not a native Hindi ear — blind human votes are the final word.

| Use | Leader on this test | Why (numbers from `scores.jsonl`, `receipts.jsonl`, `qa.json`) |
|---|---|---|
| Hindi audio drama | Gemini 3.8 Flash-Lite TTS | natural 4.75/5, acting 4.67/5, whisper −10.3 dB / anger +7.3 dB vs calm, laugh+sigh on cue, ~$0.009/min |
| Low-latency Hindi bot | Cartesia Sonic 3.6 | 0.48 s to first audio from India (median of 3), numbers 100%, kids line 5/5 |
| Indian provider | Sarvam Bulbul v3 | numbers 100%, calm narration 5/5; no acting; romanised Hinglish weak |
| Open weights on a 16 GB Mac | VoxCPM2 (Apache-2.0) | natural 4.0/5 but ~8× slower than real time; Kokoro is fast but robotic in Hindi |

Other findings: ElevenLabs v3 measurably acts (−4.4 / +5.9 dB) but the AI listener rated it flat — the two disagree.
ElevenLabs ends clips abruptly (all words present, no tail room). Cloning from a 12 s clip was weak for every model.
No model lost clarity on an 8 kHz phone line. The transcriber sometimes writes heard Hindi in Urdu script — those clips
are excluded from error rates, not counted as model errors. Public leaderboards test English only.

## Run it
```bash
python3 voice_bench.py --dry-run          # closed models: plan + cost estimate, no calls
python3 voice_bench.py --budget 0.30      # hard cap; existing clips are never remade
python3 clone_bench.py --dry-run          # synthetic reference + clone + voice changer
python3 hf_voice_bench.py                 # open models on free HF demos (no key)
python3 score.py --dry-run                # transcripts, AI listener, consistency, phone line
python3 local_bench.py kokoro             # open models on Apple Silicon via mlx-audio (use a Python 3.12 venv)
python3 qa_check.py                       # free: dead air, abrupt endings, clipping, pauses, speed outliers
python3 build_page.py                     # builds ../voice-page (the comparison page)
```
Keys are read at runtime from your own env files (see `keys()` in `voice_bench.py`) and are never printed or written.
Every call is logged to `receipts.jsonl` with time to first audio, total time, estimated cost and status.

## Rules we keep
Only synthetic or consenting voices are cloned. Paid runs need `--budget`. Rejected calls are not retried blindly.

Licence: MIT (this code). Model outputs follow each provider's terms.

## Files
`prompts.json` test lines + checklists · `catalog.json` models, prices, licences, sources · `receipts.jsonl` every call
(time to first audio, total time, est. cost, status) · `scores.jsonl` transcripts + AI-listener verdicts · `extra_scores.jsonl`
voice consistency + phone line · `qa.json` technical defects · `research/` sourced notes on closed providers, open models
and evaluation metrics. Audio is not included (provider terms vary); re-run the scripts to regenerate it.

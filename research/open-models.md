# Open-weights TTS for Hindi/Hinglish: research notes (24 Sep 2026)

How this was checked: the HF API (`/api/models`, `/api/spaces`), raw LICENSE files and model cards on HF, GitHub licence API, and live `/gradio_api/info` calls. Every model's card is at `https://huggingface.co/<repo>`. Every licence verdict below comes from the **LICENSE file** when the repo has one. When it doesn't, the row says "no LICENSE file".

## 1. What's trending (HF API, pulled today)

- **Trending** (`sort=trendingScore`): tencent/AuK, BreezeBlue/Breeze-TTS-2, hexgrad/Kokoro-82M, k2-fsa/OmniVoice, Qwen/Qwen3-TTS-1.7B-CustomVoice, **ai4bharat/IndicF5 (#7)**, openbmb/VoxCPM2, IndexTeam/IndexTTS-2.5, coqui/XTTS-v2, fishaudio/s2-pro, Supertone/supertonic-3, ResembleAI/chatterbox, bosonai/higgs-tts-3-4b, ai4bharat/indic-parler-tts.
- **Most-liked, created May–Sep 2026**: supertonic-3 (970), higgs-tts-3-4b (773), Breeze-TTS-2 (620), Audio8-0.6b (406), AuK (354), IndexTTS-2.5 (221), MOSS-TTS-v1.5 (206). New Indic model: **rumik-ai/rumik-oss-1** (6 Sep 2026).
- **TTS Arena V2** (https://tts-agi-tts-arena-v2.hf.space/api/leaderboard, RUNNING). Closed models hold the top ranks (#1 Aurora, 1580). The open-weight entries that appear: "OpenAudio S2" #15 (1525, Fish's hosted version), Chatterbox #28 (1479), Kokoro #30 (1477), Magpie Multilingual #34, Maya 1 #35, Veena #39 (1363). The arena's own "open" flag is unreliable: it marks MIT-licensed Chatterbox as closed.
- **Artificial Analysis open-weights arena** (https://artificialanalysis.ai/text-to-speech/leaderboard/provider-voice/open-weights): Breeze TTS 2 1204 > Fish S2 Pro 1120 > Step Audio EditX 1094 > Voxtral TTS 1076 > Magpie-Multi 1063 > Kokoro 1061 > Maya1 1041 > Higgs V3 1033 > Chatterbox 1021.
- **Fish S2.1**: API only. No `fishaudio/s2.1*` repo exists (API returns 401). The blog says S2.1 Pro is "available for free via API" (https://fish.audio/blog/s2-1-pro-free-api/). The open weights are **S2 Pro**.

## 2. Main table

Key: "Params / DL" = parameter count / download size from the HF API. ZG = ZeroGPU. Anonymous ZeroGPU users get **2 min of GPU per day**, free accounts 5 min (https://huggingface.co/docs/hub/spaces-zerogpu). In practice that is 1–3 heavy runs.

| Model (repo) | Params / DL | Hindi | Cloning | Emotion control | LICENSE file → commercial? | Apple Silicon | Space (status, hw) |
|---|---|---|---|---|---|---|---|
| **Fish S2 Pro** `fishaudio/s2-pro` | 4.56B (4B slow AR + 0.4B fast AR) / 11.0 GB | Yes, but "Other supported" tier. Tier 1 is ja/en/zh only | Yes (ref audio + text); clip length unverified | Inline tags, e.g. "[laugh], [whispers]" | "FISH AUDIO RESEARCH LICENSE". "Any Commercial use… requires a separate license". GitHub code: same research licence → **No** | `mlx-community/fish-audio-s2-pro-8bit` (6.7 GB). Not in mlx-audio's list, so the runtime is unverified | `artificialguybr/fish-s2-pro-zero` RUNNING, ZG (community) |
| **Higgs TTS 3** `bosonai/higgs-tts-3-4b` | 4.65B / 9.3 GB | Yes. Hindi is in the group of 85 languages with "WER/CER under 5" | Yes, zero-shot; card says the transcript "materially improves" it | `<\|emotion:elation\|>`-style tags, plus prosody and pause tags | "BOSON HIGGS TTS 3 RESEARCH AND NON-COMMERCIAL". **Exception: a "Creator Use Grant" allows monetized podcasts/videos/audiobooks** on your own channels, with attribution. APIs and apps need a paid licence. Code (GitHub boson-ai/higgs-audio) is Apache-2.0 | mlx-audio lists "Higgs Audio v3"; `Reza2kn/Higgs-Audio-v3-TTS-4bit-MLX` 2.1 GB | `multimodalart/higgs-audio-v3-tts` RUNNING, ZG |
| **Chatterbox Multilingual V3** `ResembleAI/chatterbox` + Hindi finetune `ResembleAI/Chatterbox-Multilingual-hi` | 0.5B ("same 0.5B model size") / hi repo 4.3 GB (main repo 13.9 GB holds all versions) | Yes: 23 languages, plus a **dedicated Hindi finetune** | Yes, zero-shot from a ref clip; exact length unverified | `exaggeration` (default 0.5; card: raise to "0.7 or higher" for drama) | No LICENSE on HF. GitHub LICENSE = "MIT License, Copyright (c) 2025 Resemble AI" → **Yes**. Outputs are watermarked | mlx-audio "Chatterbox (v2/v3)"; `mlx-community/chatterbox-multilingual-v3` 2.7 GB; PyTorch MPS via `example_for_mac.py` | `ResembleAI/Chatterbox-Multilingual-TTS-hi` RUNNING, ZG. `…-TTS-V3` RUNNING, ZG |
| **VoxCPM2** `openbmb/VoxCPM2` | 2.29B / 5.0 GB | Yes (30 languages) | Yes, "from a short clip". Also a mode that uses ref audio + transcript | Text "style guidance to steer emotion, pace"; voice design from a description | No LICENSE on HF. GitHub OpenBMB/VoxCPM LICENSE = Apache-2.0. Card: "free for commercial use" → **Yes** | mlx-audio "VoxCPM2"; `mlx-community/VoxCPM2-8bit` 3.2 GB, `-4bit` 2.3 GB | `openbmb/VoxCPM-Demo` RUNNING, **cpu-basic** (not ZeroGPU, so no quota) |
| **IndicF5** `ai4bharat/IndicF5` | 0.35B / 1.4 GB | **Hindi-specific** (11 Indic languages) | Yes: needs ref audio **+ its transcript** | Copies the style of the reference only | Card metadata says MIT, but **there is no LICENSE file on HF or on GitHub AI4Bharat/IndicF5**. Status: unverified. HF gate: "auto" | F5 arch; MPS not stated (unverified) | `ai4bharat/IndicF5` **RUNTIME_ERROR** |
| **OmniVoice** `k2-fsa/OmniVoice` | 0.61B / 3.3 GB | Yes (646 languages) | Yes, from a short ref clip | Voice design, non-verbal symbols | Card: code Apache-2.0, but **"pre-trained model is licensed under the CC-BY-NC"**. Its `audio_tokenizer/LICENSE` is the Boson Higgs Audio 2 Community licence → **No** | Card has an "Apple Silicon" install section; mlx-community ports (8bit 1.45 GB) | `k2-fsa/OmniVoice` RUNNING, ZG |
| **MOSS-TTS v1.5** `OpenMOSS-Team/MOSS-TTS-v1.5` | 8.49B / 17.0 GB | Yes (Hindi was added in v1.5) | Yes: "more stable voice cloning" | Duration and pronunciation control | Card Apache-2.0. **No LICENSE file** in the repo | mlx-community `MOSS-TTS-Local-Transformer-v1.5` ports. Too big for 16 GB at bf16 | `OpenMOSS-Team/MOSS-TTS-v1.5` RUNNING, ZG |
| **Svara-TTS v1** `kenpath/svara-tts-v1` (+ `svara-tts-voiceclone-beta`) | 3.3B / 13.2 GB (beta 6.6 GB) | **Indic-specific** (19 languages) | v1: fixed "Language (Gender)" voices. Cloning only in the **beta** | `<happy> <sad> <anger> <fear>` tags | Card Apache-2.0, no LICENSE file. **base_model = canopylabs/3b-hi-ft-research_release** (Orpheus → Llama-3.2-3B) | GGUF tag; MLX unverified | `kenpath/svara-tts` RUNNING, ZG (no cloning in the Space) |
| **rumik-oss 1** `rumik-ai/rumik-oss-1` | 3.38B / 7.2 GB | **Indic-specific** (22 languages), code-switched | **No**: 4 speakers (Ira, Aisha, Siya, Zoya) | tone, pace, accent, `<laugh> <sigh>`. IndicEmo 2.92/5 vs ElevenLabs v3 2.16 (their own benchmark) | CC-BY-NC-4.0 (inherits from Cohere tiny-aya) → **No** | Official `rumik-oss-1-mlx-4bit` 1.9 GB; listed in mlx-audio | `rumik-ai/rumik-oss-1` RUNNING, ZG |
| **Veena** `maya-research/Veena` | 3.78B / 7.6 GB | **Hindi + English, code-mixed** | No: 4 speakers (kavya, agastya, maitri, vinaya) | "emotional tone" (no tag list) | Card Apache-2.0, no LICENSE file. Llama arch; Llama lineage unverified | 4-bit NF4 (bitsandbytes, CUDA); Mac unverified | Community Spaces only, all broken (BUILD/RUNTIME_ERROR) |
| **Indic Parler-TTS** `ai4bharat/indic-parler-tts` | 0.94B / 3.8 GB | Yes: 4 Hindi voices (Rohit, Divya, Aman, Rani) | **No**, prompt-described voices only | Emotions are official for 10 languages, and **Hindi is not one of them** | Card Apache-2.0, no LICENSE file. Gated (contact info) | PyTorch; unverified | `ai4bharat/indic-parler-tts` RUNNING, ZG (`/gradio_api/info` returns 500) |
| **Voxtral 4B TTS** `mistralai/Voxtral-4B-TTS-2603` | ~4B / 8.0 GB | Yes (9 languages) | Benchmarked with a "10-second audio reference". Whether the open release clones any clip is unverified | "emotional range" | cc-by-nc-4.0 → **No** | mlx-audio "Voxtral TTS"; mlx-community 4bit | `mistralai/voxtral-tts-demo` RUNNING, cpu-basic |
| **Kokoro** `hexgrad/Kokoro-82M` | 82M / 0.36 GB | Hindi voices "2F 2M" (VOICES.md) | No | No | Card Apache-2.0 | mlx-audio (lists HI) | `hexgrad/Kokoro-TTS` RUNNING, ZG |
| **Qwen3-TTS** `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | 1.93B / 4.5 GB | **No Hindi** (10 languages: zh en ja ko de fr ru pt es it) | "3-second rapid voice clone" | Instruction control | Apache-2.0 (card) | Many mlx-community ports | `Qwen/Qwen3-TTS` RUNNING, ZG |
| **Supertonic 3** `Supertone/supertonic-3` | ~99M / 0.4 GB | Yes (31 languages) | Only preset styles in the open package | `<laugh> <breath> <sigh>` | LICENSE = BigScience **OpenRAIL-M** (commercial allowed, with use restrictions) | ONNX on CPU | 30 community Spaces |
| **Breeze TTS 2** `BreezeBlue/Breeze-TTS-2` | 3.47B / 7.7 GB | Card languages en/zh, 0 mentions of Hindi | Yes (ref + transcript) | "Voice Direction" | "BREEZEBLUE RESEARCH AND NON-COMMERCIAL" → **No** | `mlx-community/Breeze-TTS-2-mlx` | `BreezeBlue/breeze-tts-2-demo` RUNNING, ZG |
| Not usable for Hindi | | | | | | | |
| CosyVoice 3 `FunAudioLLM/Fun-CosyVoice3-0.5B-2512` | 0.5B / 9.7 GB | No (9 languages) | Yes | Instruct | Apache-2.0 | — | RUNNING, ZG |
| IndexTTS-2 / 2.5 `IndexTeam/IndexTTS-2(.5)` | —/ 5.9 / 5.5 GB | No (2.5: zh en ja es ar) | Yes | Yes, disentangled from timbre | LICENSE = "bilibili Model Use License". Commercial OK unless >100M MAU or >RMB 1B revenue | `mlx-community/index-tts2-mlx` | RUNNING, ZG |
| VibeVoice `microsoft/VibeVoice-1.5B` | 2.7B / 5.4 GB | No (en/zh). Community Hindi LoRAs exist (`tarun7r/vibevoice-hindi-*`) | Yes | — | MIT; card lists out-of-scope uses (e.g. impersonation), not a blanket commercial ban | — | — |
| Spark-TTS `SparkAudio/Spark-TTS-0.5B` | 0.5B / 3.9 GB | No | Yes | — | CC-BY-NC-SA-4.0 | mlx port | — |
| Dia2 `nari-labs/Dia2-2B`; Maya1 `maya-research/maya1`; Kyutai `kyutai/tts-1.6b-en_fr`; NeuTTS `neuphonic/neutts-air` | 1.9B; 3.3B; 1.6B; 0.75B | No (en; en; en/fr; en + es/fr/de nano) | Dia2 yes; Kyutai "restrict[ed]" to precomputed embeddings; NeuTTS yes | Maya1: 20+ tags | Apache; Apache; CC-BY-4.0; Apache | — | Maya1 RUNNING cpu-basic |
| Orpheus Hindi `canopylabs/3b-hi-ft-research_release` | 3.3B / 13.2 GB | Hindi | No | Tags | Card Apache, name says "research_release", Llama-3.2 base | GGUF (community) | — |
| Also no Hindi: Higgs Audio v2 (Llama-3 community licence, >100k users needs permission), MOSS-TTSD v1.0 (Apache, 3–10 s cloning), tencent/AuK (MIT; Hindi not stated) | | | | | | | |

## 3. Picks

**Top 5 for Hindi quality + cloning.** This ranking is my judgement from the evidence above. Nobody publishes a Hindi cloning benchmark that covers all five, so the founder needs to run a listening test.
1. **Fish S2 Pro**: #2 open model on Artificial Analysis (1120), with inline emotion tags. Hindi is only "other supported" tier. Non-commercial.
2. **Higgs TTS 3 4B**: Hindi is in its WER/CER<5 group, it has the richest emotion tags, and the Creator Grant allows monetized content.
3. **Chatterbox Multilingual V3 + Hindi finetune**: the only one with a dedicated Hindi checkpoint **and** MIT. It also has an exaggeration knob.
4. **VoxCPM2**: Apache, Hindi, cloning plus text style guidance, 48 kHz output.
5. **IndicF5**: Hindi-native cloning. But the licence file is missing and the Space is down.
   Close alternates: OmniVoice (NC), MOSS-TTS v1.5 (8B), Svara voiceclone-beta.

**Top 2 to run locally on a 16 GB M5** (unified memory; these estimates are weights plus a few GB of working memory):
1. **Chatterbox Multilingual V3 (Hindi)**: 0.5B params. MLX download 2.7 GB (`mlx-community/chatterbox-multilingual-v3`), PyTorch-MPS Hindi repo 4.3 GB. Estimated peak **~4–6 GB**. Supported by mlx-audio and by `example_for_mac.py`.
2. **VoxCPM2**: 2.29B params. MLX 8-bit 3.2 GB / bf16 5.0 GB. The card says "VRAM ~8 GB" (bf16, CUDA). Estimated **~5–8 GB**. Supported by mlx-audio.
   (A third option, for creator use only: Higgs TTS 3 as a 4-bit MLX community port, 2.1 GB. Its quality after 4-bit quantization is unverified.)

Disk: all three together take about 12 GB, well within the 44 GB free.

## 4. Space APIs (from live `/gradio_api/info`)

Call flow: `POST https://<sub>.hf.space/gradio_api/upload` (multipart `files=@ref.wav`) returns `["/tmp/gradio/…/ref.wav"]`. Then `POST /gradio_api/call/<fn>` with `{"data":[…]}` and pass files as `{"path":"<returned>","meta":{"_type":"gradio.FileData"}}`. That returns `{"event_id":…}`. Finally `GET /gradio_api/call/<fn>/<event_id>` gives an SSE stream, and the audio URL is in the `complete` event. Send an `Authorization: Bearer hf_…` header to use a free account's 5-minute quota instead of the anonymous 2 minutes.

| Space → subdomain | fn | data order (default) |
|---|---|---|
| ResembleAI/Chatterbox-Multilingual-TTS-hi → `resembleai-chatterbox-multilingual-tts-hi` | `generate_tts_audio` | text_input, audio_prompt_path_input(file), exaggeration_input(0.5), temperature_input(0.8), seed_num_input(0), cfgw_input(0.5) |
| ResembleAI/Chatterbox-Multilingual-TTS-V3 → `resembleai-chatterbox-multilingual-tts-v3` | `generate_tts_audio` | text_input, audio_prompt_path_input(file), language_id_input('hi'), exaggeration_input(0.5), temperature_input(0.8), seed_num_input(0), cfgw_input(0.5) |
| artificialguybr/fish-s2-pro-zero → `artificialguybr-fish-s2-pro-zero` | `tts_inference` (+ `transcribe_audio(audio_path)`) | text, ref_audio(file), ref_text, max_new_tokens(1024), chunk_length(200), top_p(0.7), repetition_penalty(1.2), temperature(0.7) |
| multimodalart/higgs-audio-v3-tts → `multimodalart-higgs-audio-v3-tts` | `synthesize` (+ `transcribe(reference_audio)`) | text, reference_audio(file), reference_text, temperature(0.7), top_p(0.95), top_k(50), max_new_tokens(2048), seed(-1) |
| openbmb/VoxCPM-Demo → `openbmb-voxcpm-demo` | `generate` (+ `_run_asr_if_needed(checked, audio_path)`) | text_input, control_instruction(''), reference_wav_path_input(file/None), use_prompt_text(False), prompt_text_input(''), cfg_value_input(2.0), do_normalize(False), denoise(False) |
| k2-fsa/OmniVoice → `k2-fsa-omnivoice` | `_clone_fn` | text, lang('Hindi' of 646 or 'Auto'), ref_aud(file), ref_text, instruct(req; '' ok, unverified), ns(32), gs(2.0), dn(True), sp(1.0), du(req; null for auto, unverified), pp(True), po(True) |
| kenpath/svara-tts → `kenpath-svara-tts` | `generate_speech` | language('Hindi (हिन्दी)'), gender('Female'), text, temperature(0.7), top_p(0.8), repetition_penalty(1.1), max_new_tokens(2048). No cloning |
| rumik-ai/rumik-oss-1 → `rumik-ai-rumik-oss-1` | `synthesize` | text, speaker(Ira/Zoya/Aisha/Siya), tone(happy/sad/angry/excited/professional), accent('Hindi accent'), pace, mode('Controls'), temperature(0.8), top_k(30), max_new_tokens(2048), seed(-1). No cloning |

## 5. Licence traps

- **The README tag can differ from the licence file, or there is no licence file at all.** IndicF5 is tagged MIT but has **no LICENSE file** on HF or GitHub. OmniVoice has no licence tag, and its card says the **weights are CC-BY-NC** (Emilia data) even though the code is Apache. Its bundled tokenizer carries the Higgs Audio 2 licence. Voxtral's weights are CC-BY-NC because they "inherit" the licence of the voice references.
- **"Open" usually means research-only.** Fish S2 Pro, Higgs TTS 3, Breeze TTS 2, rumik-oss-1, Spark-TTS and XTTS-v2 (CPML) are all non-commercial. For Fish, the **code** repo also moved to the research licence.
- **Higgs TTS 3's creator carve-out** allows monetized YouTube, podcasts and audiobooks on channels you own, with attribution and recorded consent for cloned voices. It does **not** allow APIs, apps or telephony.
- **Llama inheritance.** Svara v1's base is `canopylabs/3b-hi-ft-research_release` (Orpheus → Llama-3.2-3B). Even though the card says Apache, the Llama 3.2 Community Licence (attribution, AUP) probably applies, and the parent is labelled "research release". Veena is also Llama-architecture, but its lineage is unverified.
- **Threshold clauses.** The bilibili licence (IndexTTS) requires a separate licence above 100M MAU or RMB 1B revenue. Higgs Audio 2 requires one above 100k annual users. MisoTTS requires attribution above 50M MAU or $10M/month. Also check training bans: Fish, Higgs 3 and bilibili all forbid using outputs to train other models.
- **Consent terms.** Higgs 3 requires "explicit, verifiable consent" records for cloned voices. IndicF5's card says clone only voices "for which you have explicit permission".

# TTS benchmark rubric: Hindi micro-drama (D) + Hindi/Hinglish kids voice bot (B)

Researched 26 Sep 2026. [n] = source number (listed at the end). **UNVERIFIED** = I could not find a primary source for it.

## Rubric

| # | Metric | What it measures | Cheap way to measure | Good / OK / Bad (source) | Use |
|---|---|---|---|---|---|
| 1 | **Pairwise preference (Elo / Bradley-Terry)** | Which voice people prefer overall | Blind A/B test with 5–10 native Hindi listeners, random order, names hidden; fit Bradley-Terry. Use AI4Bharat's 6 axes: intelligibility, expressiveness, voice quality, liveliness, hallucinations, noise | Relative ranking only, no absolute bar. Method from [1][2]; Indic axes from [3] | Both |
| 2 | **CMOS vs. a real recording** | How close the model is to a human recording | −3…+3 side-by-side score against a human take | Good: \|CMOS\| < 0.1, which Seed-TTS calls "insignificant"; Seed-TTS scored −0.07 [5] | D |
| 3 | **CER (Hindi) / WER (Hinglish)** | Did it say the words: skips, mumbles, invented words | Transcribe with IndicWhisper; compare to the script. **Also transcribe a human recording of the same lines** to find the ASR's own error floor | IndicWhisper already gets 10.3% WER on Hindi Kathbath and 7.6% on IndicTTS [8], so judge TTS **relative to that human floor**. Good ≤ human + 1 pt; bad ≥ 2× human. For scale, English Seed-TTS was 2.25% vs. 2.14% for human [5] | Both |
| 4 | **Long-form stability** | Skips and hallucinations over a whole episode | Synthesize 1,500+ words with 3–5 seeds; report mean **and worst-seed** WER. Flag a skip at ≥10 deleted words in a row, a hallucination at ≥20 wrong or inserted words [11] | Qwen3-TTS-0.6B: 5.4% worst-seed WER under 500 words, 35.2% at 1,500+ words [11]. Good = worst seed within 1.5× the short-text WER; bad = any skip or hallucination | D |
| 5 | **Speaker similarity (SIM)** | Does the clone sound like the reference voice | Cosine similarity of WavLM-large speaker-verification embeddings [4] (or ECAPA). Numbers from different embedding models can't be compared | Human-vs-human: 0.73 on English, 0.75 on Chinese; Seed-TTS 0.76 [5]; F5-TTS 0.67 [6]. Good ≥ 0.70; OK 0.60–0.70; bad < 0.55 (the cut-offs are my reading of these numbers) | Both |
| 6 | **Cross-episode consistency (windowed SIM)** | Same character voice across episodes and within long clips | SIM between episode N and episode 1 of the same character, plus SIM on 8-second windows [11] | SwanBench found long-form "Timbre Consistency" is where models fall short [10]. Good = lowest window ≥ 0.9 × the average | D |
| 7 | **Automatic MOS (UTMOSv2 / DNSMOS)** | Naturalness and noise, estimated without listeners | UTMOSv2 (MIT) [12]; DNSMOS P.835 gives separate speech, noise and overall scores [13] | UTMOS was trained on **English-only** data (the VoiceMOS main track is "all in English" [14]), so on Hindi use it **only to catch broken or noisy audio**, never to rank models. MOS predictors also get unreliable near human quality [15] | Both (screen only) |
| 8 | **Emotion accuracy** | Did the model act the requested emotion | Tag each line with the target emotion; score with emotion2vec+ large (9 classes, about 42.5k hours of training data) [16]. Test "text-unrelated" lines too, where the words don't give the emotion away | CosyVoice 3 scored happy 0.86 / sad 0.64 / angry 0.72 when the text matched the emotion, but 0.64 / 0.44 / 0.48 when it didn't [17]. Good ≥ 0.7 on text-unrelated lines. Fear and surprise are hardest in Indic languages [18]. **Not validated on Hindi**, so confirm with native listeners | D |
| 9 | **Non-verbal sounds** | Laughs, sighs, gasps, crying on cue | Checklist of 20 tagged cues; a listener marks each as present / natural / wrong. EmergentTTS-Eval has a "paralinguistics" category judged by an audio-language model [7] | Good ≥ 90% present and natural; bad < 70% (my own cut-offs; no published bar) | D |
| 10 | **Perceived TTFA (time to first audio)** | Time until the listener hears sound | Coval's formula: first chunk arrival + leading silence before the first audible sample [19]. Report p50 and p95 over 100+ calls on the real network | TTS share of the budget: good ≤ 150 ms; OK 150–250 ms; bad > 250 ms. Vapi quotes "50–250 ms when warmed" [20]; Hamming's target is 100–200 ms [21] | B |
| 11 | **End-to-end turn latency** | From user stops talking to bot starts talking | Retell's per-call `e2e` p50/p90/p99 [22] | Humans answer in about 200 ms on average (mean +208 ms; most common gap 0–200 ms) [23]. Vapi: "p50 < 500 ms, p95 < 800 ms" [20]. Hamming: under 1 s good; 1.4–1.7 s is the median, and users notice it [21] | B |
| 12 | **Phone-line (8 kHz μ-law) robustness** | Quality after the phone line strips detail | Convert output to 8 kHz μ-law (Twilio's only phone format [24]), then re-run #3 and #1 | Good = CER goes up by less than 1 point and people still prefer it. Speech band is about 300–3,400 Hz [25] (secondary source) | B |
| 13 | **Loudness + true peak** | Consistent volume after platform normalization | ffmpeg `loudnorm` / pyloudnorm | Spotify: −14 LUFS, true peak ≤ −1 dBTP [26]. AES: drama −18 LUFS, peak ≤ −1 dBTP [27]. The widely quoted YouTube −14 and Instagram numbers are **UNVERIFIED** (YouTube and Instagram don't publish them). Aim for −14 LUFS, peak ≤ −1 dBTP | D |
| 14 | **Speech rate for kids** | Speed children can follow | Syllables per second from the ASR timestamps | Kindergarten and 2nd-grade children understood more at 2.6–3.4 syllables/sec than at 4.7–6.3 [28]. Good ≤ 3.5 syll/s. **No Hindi-specific words-per-minute guidance found (UNVERIFIED)** | B |

## What matters most for our two uses

- **Hindi voices can't be ranked by English-trained scorers.** UTMOS was trained on English only [14], CV3-Eval leaves out Hindi [17], and emotion2vec hasn't been tested on Hindi. Final model choices should rest on a small blind A/B test with native listeners (#1), scored on AI4Bharat's axes, which already include code-mixed sentences [3].
- **Judge intelligibility against a human baseline.** Hindi ASR already gets about 8–10% WER on clean speech [8], so a raw WER number mostly measures the ASR, not the TTS.
- **Drama: test long episodes, not single lines.** Short-text WER is saturated. Failures show up past 1,500 words (worst-seed WER 5% → 35%) [11], and the voice drifts over long takes [10]. Worst-seed WER (#4) and windowed SIM (#6) are the gates.
- **Drama: acting must come from the instruction, not the words.** Emotion accuracy drops sharply when the text doesn't signal the emotion [17]. Test lines where the emotion is only in the direction.
- **Bot: latency is mostly the platform, not the voice.** The TTS contributes roughly 50–250 ms [20] out of a ~500 ms p50 target [20]. Turn detection, interruption sensitivity, backchannels ("uh-huh") and wait time are Retell/Vapi settings [22][29]. So benchmark the TTS on perceived TTFA (#10) only, and measure end-to-end latency (#11) separately as a platform check.
- **Bot: test the voice after the phone line.** On phone calls the audio is always 8 kHz μ-law [24]. A voice that wins on studio-quality audio can lose its breathiness and clarity on a call, so re-run #3 and #1 on converted audio (#12).
- **Kids: slow speech and safety come before voice quality.** Keep speech around 3 syllables/sec or slower [28]. In India, the DPDP Act §9 requires "verifiable consent of the parent" and bans "tracking or behavioural monitoring of children" [30]. Under US COPPA, a child's voice recording can be kept without parental consent only if it is used just for that request and deleted right after [31]. UNICEF's 2025 AI-and-children guidance now specifically covers AI companions [32].
- **Harnesses we can align with:** EmergentTTS-Eval (Apache-2.0) [7], CV3-Eval (Apache-2.0), VERSA (90+ metrics, Apache-2.0) [9], UTMOSv2 (MIT), Coval benchmarks (Apache-2.0 per its docs; GitHub doesn't detect the licence) [19], SpeechArenaBench (MIT) [3]. **Seed-TTS-Eval has no LICENSE file** (checked through the GitHub API), and SwanBench is CC BY-NC-SA [10]. Treat both as reference only.

## Sources

1. Artificial Analysis TTS methodology: "pairwise votes using a Bradley-Terry model"; names hidden, order randomized. https://artificialanalysis.ai/text-to-speech/methodology
2. TTS Arena (Hugging Face): "Model names will be revealed only after a vote". https://huggingface.co/blog/arena-tts
3. AI4Bharat SpeechArenaBench: 10 Indic languages including Hindi, 120K+ comparisons, 1,900+ raters, 6 axes, MIT. https://huggingface.co/datasets/ai4bharat/SpeechArenaBench ; paper https://arxiv.org/abs/2604.21481
4. Seed-TTS-Eval: Whisper-large-v3 for English, Paraformer-zh for Chinese, "WavLM-large fine-tuned on the speaker verification task". https://github.com/BytedanceSpeech/seed-tts-eval
5. Seed-TTS paper, Table 1: English WER 2.249 / SIM 0.762 / CMOS −0.07; human 2.143 / 0.730; "absolute CMOS…less than 0.1…insignificant". https://arxiv.org/html/2406.02430v1
6. F5-TTS: Seed-TTS test-en ground truth SIM 0.73, F5-TTS 0.67; RTF 0.15. https://arxiv.org/html/2410.06885v1
7. EmergentTTS-Eval: 1,645 cases, 6 categories including paralinguistics and emotions, audio-model judge, Apache-2.0. https://arxiv.org/abs/2505.23009 ; https://github.com/boson-ai/EmergentTTS-Eval-public
8. Vistaar / IndicWhisper: Hindi Kathbath 10.3 WER, IndicTTS 7.6 WER, MIT. https://github.com/AI4Bharat/vistaar
9. VERSA: "over 90 evaluation/profiling metrics". https://github.com/wavlab-speech/versa
10. SwanBench-Speech: 1,101 samples averaging 228.6 words; "deficit in Timbre Consistency"; CC BY-NC-SA 4.0. https://arxiv.org/html/2605.28618
11. Taming Long-form TTS: skip ≥10 words, hallucination ≥20 words; worst-seed WER 5.4% → 35.2%; 8 s windowed SIM. https://arxiv.org/html/2609.16989
12. UTMOS (VoiceMOS 2022): https://arxiv.org/abs/2204.02152 ; UTMOSv2 (MIT): https://github.com/sarulab-speech/UTMOSv2
13. DNSMOS P.835: "speech quality (SIG)…background noise quality (BAK)…overall quality (OVRL)". https://arxiv.org/abs/2110.01763
14. VoiceMOS 2022: "all of the samples in the main track dataset are in English". https://arxiv.org/pdf/2203.11389
15. TTSDS2: MOS predictors become unreliable near human quality; only metric with Spearman > 0.5 in every domain; 14 languages. https://arxiv.org/abs/2506.19441v1
16. emotion2vec+ large: 9 classes, 42,526 hours of training data. https://huggingface.co/emotion2vec/emotion2vec_plus_large
17. CosyVoice 3 / CV3-Eval: emotion accuracy figures; 9 languages, no Hindi; uses emotion2vec. https://arxiv.org/html/2505.17589v1
18. Rasa (AI4Bharat): "challenges in generating specific emotions, such as fear and surprise". https://arxiv.org/abs/2407.14056
19. Coval methodology: "TTFA = (first audio chunk arrival − synthesis start) + leading silence". https://github.com/coval-ai/benchmarks/blob/main/docs/methodology.md
20. Vapi: "p50 < 500 ms, p95 < 800 ms"; TTS "50-250 ms when warmed". https://vapi.ai/blog/speech-latency
21. Hamming: TTS "100-200ms TTFB with streaming"; 1.4–1.7 s is the industry median. https://hamming.ai/resources/voice-ai-latency-whats-fast-whats-slow-how-to-fix-it
22. Retell latency docs: e2e = "from when the user stops talking to when the agent starts talking"; tts = "to the first audio byte"; p50/p90/p99. https://docs.retellai.com/reliability/check-actual-latency
23. Stivers et al. 2009, PNAS: "overall mode of 0 ms"; mean about +208 ms across 10 languages. https://pmc.ncbi.nlm.nih.gov/articles/PMC2705608/
24. Twilio Media Streams: encoding "always audio/x-mulaw", rate "always 8000". https://www.twilio.com/docs/voice/media-streams/websocket-messages
25. G.711 300–3,400 Hz band (secondary source). https://www.voipmonitor.org/doc/Audio_Codecs_-_Comprehensive_Guide
26. Spotify: "-14dB integrated LUFS", "below -1dB TP". https://support.spotify.com/us/artists/article/loudness-normalization/
27. AES TD1008: Drama −18 LUFS, News/Talk −18 LUFS; true peak "not exceed -1 dBTP". https://aes.org/wp-content/uploads/2024/01/20210924_TD1008_v3.13.pdf
28. Berry & Erickson 1973, JSHR: children understood more at 2.6 and 3.4 syllables/sec than at 4.7–6.3. https://eric.ed.gov/?id=EJ117612
29. Vapi pipeline defaults: waitSeconds 0.4; interruption voiceSeconds 0.2; backoff 1.0 s. https://docs.vapi.ai/customization/voice-pipeline-configuration
30. DPDP Act 2023 §9(1) and §9(3). https://www.dpdpa.com/dpdpa2023/chapter-2/section9.html
31. FTC COPPA amended rule (Federal Register, 22 Apr 2025). The voice-recording exception is taken from law-firm summaries; I did not read the rule text itself. https://www.federalregister.gov/documents/2025/04/22/2025-05904/childrens-online-privacy-protection-rule
32. UNICEF Guidance on AI and Children v3 (Dec 2025). https://www.unicef.org/innocenti/reports/policy-guidance-ai-children

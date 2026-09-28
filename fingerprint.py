"""Voice fingerprints: is it the same person? Free, local (Microsoft WavLM speaker-verification model).

  .venv/bin/python fingerprint.py a.wav b.wav            # similarity of two clips (0-1)
  .venv/bin/python fingerprint.py --calibrate             # same-voice vs different-voice scores on round-1 clips

Model: microsoft/wavlm-base-plus-sv. Its model card suggests cosine >= 0.86 means the same speaker.
Scores from different embedding models are not comparable, so we also calibrate on our own clips.
"""
import glob
import itertools
import json
import os
import subprocess
import sys

os.environ.setdefault("HF_HUB_CACHE", os.path.expanduser("~/projects/model-lab/models/voice/hub"))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from transformers import AutoFeatureExtractor, WavLMForXVector  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "microsoft/wavlm-base-plus-sv"
_fx = _model = None
_cache = {}


def load():
    global _fx, _model
    if _model is None:
        _fx = AutoFeatureExtractor.from_pretrained(REPO)
        _model = WavLMForXVector.from_pretrained(REPO).eval()
    return _fx, _model


def audio16k(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def embed(path):
    if path in _cache:
        return _cache[path]
    fx, model = load()
    wav = audio16k(path)
    with torch.no_grad():
        inp = fx(wav, sampling_rate=16000, return_tensors="pt")
        e = model(**inp).embeddings[0]
        e = torch.nn.functional.normalize(e, dim=-1).numpy()
    _cache[path] = e
    return e


def sim(a, b):
    return float(np.dot(embed(a), embed(b)))


def calibrate():
    out = os.path.join(HERE, "out-voice")
    same, diff = [], []
    reps = {}
    for f in glob.glob(os.path.join(out, "*", "V7*.*")):
        reps.setdefault(os.path.basename(os.path.dirname(f)), []).append(f)
    for m, fs in reps.items():
        for a, b in itertools.combinations(sorted(fs), 2):
            same.append((m, sim(a, b)))
    firsts = [(m, sorted(fs)[0]) for m, fs in reps.items()]
    for (m1, a), (m2, b) in itertools.combinations(firsts, 2):
        diff.append((m1 + " vs " + m2, sim(a, b)))
    s = [x for _, x in same]
    d = [x for _, x in diff]
    print("same voice, same line, 3 runs: n=%d  min %.3f  median %.3f" % (len(s), min(s), float(np.median(s))))
    print("different voices, same line:   n=%d  max %.3f  median %.3f" % (len(d), max(d), float(np.median(d))))
    for m, x in sorted(same, key=lambda t: t[1])[:6]:
        print("  lowest same-voice:", m, round(x, 3))
    for m, x in sorted(diff, key=lambda t: -t[1])[:6]:
        print("  highest different-voice:", m, round(x, 3))
    json.dump({"same": same, "diff": diff}, open(os.path.join(HERE, "fingerprint_calibration.json"), "w"), indent=0)


if __name__ == "__main__":
    if sys.argv[1:] == ["--calibrate"]:
        calibrate()
    else:
        print("%.3f" % sim(sys.argv[1], sys.argv[2]))

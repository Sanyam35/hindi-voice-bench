#!/bin/bash
# Round 2: Sarvam, Cartesia, Inworld (paid from their free signup credits) + score every clip not yet scored
# (includes the open models run on this Mac). Hard caps: $0.20 voices, $1.00 scoring.
set -u
cd "$(dirname "$0")"
echo "== 1/2  Sarvam Bulbul v3, Cartesia Sonic 3.6, Inworld TTS-2 + TTS-2 Flash (cap \$0.20, free credits)"
python3 -u voice_bench.py --budget 0.20 --el-credits 0 --only sarvam__bulbul-v3,cartesia__sonic-3.6,inworld__tts-2,inworld__tts-2-flash 2>&1 | tee -a run.log
echo "== 2/2  Scoring new clips (cap \$1.00)"
python3 -u score.py --budget 1.00 2>&1 | tee -a run.log
echo
echo "DONE. Go back to Claude and say: done"

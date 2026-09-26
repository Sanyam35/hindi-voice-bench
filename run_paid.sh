#!/bin/bash
# One command for the whole voice bench. Hard caps: $1.91 in total and 5,000 ElevenLabs credits.
# Safe to re-run: finished clips and scores are never redone, so a second run only fills gaps.
set -u
cd "$(dirname "$0")"
echo "== 1/4  Voices: 9 closed models x 8 lines (cap \$0.30 + 3,500 ElevenLabs credits)"
python3 -u voice_bench.py --budget 0.30 --el-credits 3500 2>&1 | tee -a run.log
echo "== 2/4  Clone test (synthetic 'Dadi' voice) + voice changer (cap \$0.01 + 1,500 credits)"
python3 -u clone_bench.py --budget 0.01 --el-credits 1500 2>&1 | tee -a run.log
echo "== 3/4  Open models on free Hugging Face demos (\$0; may wait in queues)"
python3 -u hf_voice_bench.py 2>&1 | tee -a run.log
echo "== 4/4  Scoring: transcripts + AI listener + consistency + phone-line check (cap \$1.60)"
python3 -u score.py --budget 1.60 2>&1 | tee -a run.log
echo
echo "DONE. Go back to Claude and say: done"

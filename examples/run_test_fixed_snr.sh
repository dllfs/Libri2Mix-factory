#!/usr/bin/env bash
set -euo pipefail

python ../add_factory_noise.py \
  --librimix-root /path/to/Libri2Mix \
  --noise-dir /path/to/factory_noise \
  --output-root /path/to/Libri2Mix-Factory \
  --sample-rate 16000 \
  --mode max \
  --splits test \
  --input-type mix_clean \
  --snr-list -5 0 5 10 \
  --seed 1234

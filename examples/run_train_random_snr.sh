#!/usr/bin/env bash
set -euo pipefail

python ../add_factory_noise.py \
  --librimix-root /path/to/Libri2Mix \
  --noise-dir /path/to/factory_noise \
  --output-root /path/to/Libri2Mix-Factory \
  --sample-rate 16000 \
  --mode max \
  --splits train-100 dev \
  --input-type mix_clean \
  --snr-min -5 \
  --snr-max 15 \
  --seed 1234

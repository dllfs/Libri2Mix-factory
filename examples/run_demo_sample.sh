#!/usr/bin/env bash
set -euo pipefail

python ../add_factory_noise.py \
  --librimix-root ./demo_data/Libri2Mix \
  --noise-dir ./demo_data/factory_noise \
  --output-root ./demo_output/Libri2Mix-Factory \
  --sample-rate 16000 \
  --mode max \
  --splits dev \
  --input-type mix_clean \
  --snr-list -5 0 5 \
  --seed 1234

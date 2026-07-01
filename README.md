# Libri2Mix Factory Noise

`libri2mix_factory_noise` creates a Libri2Mix-derived dataset with added
factory or industrial noise. It reads mixtures from an existing Libri2Mix
corpus, adds controlled noise at a target SNR, and writes a new dataset such as
`Libri2Mix-Factory`.

The script does not overwrite, edit, or reorganize the official Libri2Mix
dataset. All generated audio and metadata are written under `--output-root`.

## What Is Included

This repository includes:

- the noise-addition script,
- example commands,
- documentation,
- tests for SNR scaling,
- a tiny listening sample in `examples/audio_samples/`,
- tiny demo input data in `examples/demo_data/` so the script can be run
  immediately after cloning.

This repository does not include the full Libri2Mix corpus or a full
factory-noise dataset. Those audio datasets are large and have their own
licenses, so users should keep them outside the Git repository and pass their
locations with `--librimix-root` and `--noise-dir`.

Typical local layout:

```text
/data/Libri2Mix/                  # official or generated Libri2Mix corpus
/data/factory_noise/              # your factory/industrial wav/flac files
/data/Libri2Mix-Factory/          # generated output from this script
```

On this machine during development, the test paths were:

```text
/export/home3/n2500485g/Code/librimix_subset_test/Libri2Mix
/export/home3/n2500485g/Code/librimix_subset_test/factory_noise_16k
/export/home3/n2500485g/Code/librimix_subset_test/Libri2Mix-Factory-random
```

Do not commit full generated datasets to GitHub. Commit only small examples,
code, documentation, and tests.

## Quick Demo After Clone

After installing the requirements, you can run a tiny included demo without
downloading Libri2Mix:

```bash
cd examples
./run_demo_sample.sh
```

This reads:

```text
examples/demo_data/Libri2Mix/wav16k/max/dev/mix_clean/demo_mix_clean.wav
examples/demo_data/factory_noise/gearbox_factory_noise.wav
```

and writes demo outputs to:

```text
examples/demo_output/Libri2Mix-Factory/
```

The demo data is intentionally tiny. It only verifies that the command-line
workflow, output folders, audio writing, and metadata generation work. For real
experiments, use a full Libri2Mix corpus and a full factory-noise directory.

## Listen To A Sample

Small example WAV files are included in:

```text
examples/audio_samples/
```

Start with:

```text
examples/audio_samples/04_AB_before_then_after_first2s.wav
```

That file plays a short snippet before factory noise, then a short silence,
then the same snippet after factory noise. The same folder also
contains the clean mixture, the scaled noise that was actually added, and the
final noisy mixture.

For the included sample, a DCASE gearbox noise clip was added at `-5 dB` SNR so
the factory noise is easy to hear. The original factory-noise file was longer
than the mixture, so the default `--noise-long-policy random_crop` selected a
crop. If a noise file is shorter than the target mixture, the default
`--noise-short-policy loop` repeats the noise until it reaches the mixture
length.

## Recommended Defaults

For most experiments, start with:

- `--input-type mix_clean`, so factory noise is added to clean speech mixtures.
- `--mode max`, which keeps full utterance duration.
- Random train/dev SNRs sampled from `[-5, 15]` dB.
- Fixed test SNRs such as `-5, 0, 5, 10` dB.

Use `mix_both` only if you intentionally want WHAM/Libri2Mix background noise
plus factory noise.

## Installation

```bash
pip install -r requirements.txt
```

## Random Train/Dev Example

```bash
python add_factory_noise.py \
  --librimix-root /data/Libri2Mix \
  --noise-dir /data/factory_noise \
  --output-root /data/Libri2Mix-Factory \
  --sample-rate 16000 \
  --mode max \
  --splits train-100 dev \
  --input-type mix_clean \
  --snr-min -5 \
  --snr-max 15 \
  --seed 1234
```

## Fixed Test SNR Example

```bash
python add_factory_noise.py \
  --librimix-root /data/Libri2Mix \
  --noise-dir /data/factory_noise \
  --output-root /data/Libri2Mix-Factory \
  --sample-rate 16000 \
  --mode max \
  --splits test \
  --input-type mix_clean \
  --snr-list -5 0 5 10 \
  --seed 1234
```

## Expected Input Layout

For 16 kHz data, the script expects folders such as:

```text
{librimix_root}/wav16k/max/train-100/mix_clean/*.wav
{librimix_root}/wav16k/max/dev/mix_clean/*.wav
{librimix_root}/wav16k/max/test/mix_clean/*.wav
```

For 8 kHz data, use `--sample-rate 8000`:

```text
{librimix_root}/wav8k/max/train-100/mix_clean/*.wav
```

Factory noise files are collected recursively from `--noise-dir`. Supported
extensions are `.wav` and `.flac`. Mixture and noise files must have the same
sample rate. Resampling is not implemented in this v1 script; if a mismatch is
found, the script raises a clear error.

Multichannel audio is converted to mono by averaging channels.

## Expected Output Layout

Random SNR mode writes one output subset per split:

```text
{output_root}/wav16k/max/train-100/mix_factory/*.wav
{output_root}/wav16k/max/train-100/noise_factory/*.wav
{output_root}/wav16k/max/train-100/metadata/metadata_factory.csv
```

Fixed SNR mode writes one subset per SNR:

```text
{output_root}/wav16k/max/test/snr_-5/mix_factory/*.wav
{output_root}/wav16k/max/test/snr_-5/noise_factory/*.wav
{output_root}/wav16k/max/test/snr_-5/metadata/metadata_factory.csv

{output_root}/wav16k/max/test/snr_0/mix_factory/*.wav
{output_root}/wav16k/max/test/snr_0/noise_factory/*.wav
{output_root}/wav16k/max/test/snr_0/metadata/metadata_factory.csv
```

`noise_factory` contains the scaled, time-aligned noise actually added to each
mixture. This makes debugging and reproducibility easier.

## Metadata

Each generated subset has:

```text
metadata/metadata_factory.csv
```

The metadata records the utterance id, split, sample rate, mode, input type,
input path, output paths, selected factory noise path, target SNR, measured SNR,
noise crop offsets, noise scale, short/long noise policies, normalization
settings, peak before normalization, normalization gain, loop status, and seed.

These columns make it possible to identify the exact noise file, crop, scale,
and SNR used for every generated mixture.

## `mix_clean` vs `mix_both`

`mix_clean` means factory noise is added to the clean speech mixture. This is
the safest default because the resulting SNR is easier to interpret.

`mix_both` means factory noise is added on top of the existing noisy Libri2Mix
mixture. This creates WHAM/Libri2Mix noise plus factory noise, so the acoustic
condition is more complex and the factory SNR is not the only noise condition
present.

## `min` vs `max`

Libri2Mix `min` mixtures are cut to the shorter source duration. Libri2Mix
`max` mixtures keep the longer/full source duration. This tool supports both,
but `max` is often convenient for full-duration noisy speech experiments.

## SNR Scaling

The script uses:

```text
SNR = 10 * log10(P_speech / P_noise_scaled)
```

where:

```text
P_speech = mean(speech ** 2)
P_noise = mean(noise ** 2)
```

Noise is scaled with:

```python
scale = sqrt(P_speech / (P_noise * 10 ** (snr_db / 10)))
noise_scaled = scale * noise
mixture_out = speech + noise_scaled
```

By default, `--normalize peak` scales both the final mixture and scaled noise
by the same gain if the mixture peak exceeds `--clip-threshold`. This preserves
the measured SNR while avoiding clipping.

## Reproducibility

All random operations are controlled by `--seed`: SNR sampling, noise-file
selection, and random noise crops. The metadata also stores the seed and the
exact crop offsets used for each utterance.

Use `--dry-run --limit N` to preview planned outputs without writing audio.

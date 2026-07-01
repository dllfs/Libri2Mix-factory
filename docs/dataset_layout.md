# Dataset Layout

This project reads an existing Libri2Mix corpus and writes a separate derived
dataset with factory noise. The original Libri2Mix files are never modified.

## Expected Input

Libri2Mix is organized by sample rate, mode, split, and mixture type:

```text
{librimix_root}/wav16k/max/train-100/mix_clean/*.wav
{librimix_root}/wav16k/max/train-360/mix_clean/*.wav
{librimix_root}/wav16k/max/dev/mix_clean/*.wav
{librimix_root}/wav16k/max/test/mix_clean/*.wav
```

For 8 kHz data, use `--sample-rate 8000`, which maps to `wav8k`:

```text
{librimix_root}/wav8k/max/train-100/mix_clean/*.wav
```

If `--input-type mix_both` is selected, the script reads from:

```text
{librimix_root}/wav16k/max/{split}/mix_both/*.wav
```

Example input folder:

```text
/data/Libri2Mix/wav16k/max/train-100/mix_clean
```

## Random SNR Output

In random SNR mode, each utterance is generated once with an SNR sampled from
`--snr-min` to `--snr-max`:

```text
{output_root}/wav16k/max/train-100/mix_factory/*.wav
{output_root}/wav16k/max/train-100/noise_factory/*.wav
{output_root}/wav16k/max/train-100/metadata/metadata_factory.csv
```

## Fixed SNR Output

In fixed SNR mode, each requested SNR gets its own subset:

```text
{output_root}/wav16k/max/test/snr_-5/mix_factory/*.wav
{output_root}/wav16k/max/test/snr_-5/noise_factory/*.wav
{output_root}/wav16k/max/test/snr_-5/metadata/metadata_factory.csv

{output_root}/wav16k/max/test/snr_0/mix_factory/*.wav
{output_root}/wav16k/max/test/snr_0/noise_factory/*.wav
{output_root}/wav16k/max/test/snr_0/metadata/metadata_factory.csv
```

Example fixed-SNR folder:

```text
/data/Libri2Mix-Factory/wav16k/max/test/snr_0/mix_factory
```

## Noise Files

Factory noise files are collected recursively from `--noise-dir`. Supported
extensions are:

```text
.wav
.flac
```

Noise files must have the same sample rate as the selected Libri2Mix corpus.
Multichannel audio is converted to mono by averaging channels.

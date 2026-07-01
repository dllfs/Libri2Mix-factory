# Audio Samples

This folder contains a tiny listening example so users can hear what the tool
does before generating a full dataset.

Files:

```text
01_before_mix_clean.wav
02_added_factory_noise_scaled.wav
03_after_mix_factory.wav
04_AB_before_then_after_first2s.wav
05_scaled_noise_first2s.wav
```

Recommended first listen:

```text
04_AB_before_then_after_first2s.wav
```

It contains:

```text
short snippet before factory noise
short silence
same snippet after factory noise
```

Sample details:

```text
utt_id: 2412-153948-0002_7850-111771-0009
sample_rate: 16000
target_snr_db: -5
actual_snr_db: -4.999999678
noise_source: DCASE gearbox anomaly example
noise_short_policy: loop
noise_long_policy: random_crop
noise_was_looped: False
noise_start_sample: 19247
noise_end_sample: 152047
noise_scale: 2.975832812
normalize: peak
was_normalized: False
normalization_gain: 1
```

For this sample, the original factory-noise file was longer than the Libri2Mix
mixture, so the script selected a random crop, scaled it to -5 dB SNR, and
added it to `mix_clean`. This is intentionally much noisier than the default
random train/dev example.

These files are examples only. They are not a replacement for downloading or
generating Libri2Mix and collecting your own factory/industrial noise files.

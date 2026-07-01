#!/usr/bin/env python3
"""Add factory/industrial noise to an existing Libri2Mix corpus.

This script reads mixtures from an official Libri2Mix directory and writes a
new derived dataset. It never edits the input corpus.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import soundfile as sf
from tqdm import tqdm


EPS = 1e-12
AUDIO_EXTENSIONS = {".wav", ".flac"}
METADATA_COLUMNS = [
    "utt_id",
    "split",
    "sample_rate",
    "mode",
    "input_type",
    "input_mix_path",
    "output_mix_path",
    "output_noise_path",
    "factory_noise_path",
    "target_snr_db",
    "actual_snr_db",
    "noise_start_sample",
    "noise_end_sample",
    "noise_scale",
    "noise_short_policy",
    "noise_long_policy",
    "normalize",
    "was_normalized",
    "peak_before_normalization",
    "normalization_gain",
    "noise_was_looped",
    "seed",
]


@dataclass(frozen=True)
class NoiseSegment:
    samples: np.ndarray
    start_sample: int
    end_sample: int
    was_looped: bool


@dataclass(frozen=True)
class OutputPlan:
    split: str
    snr_db: float
    crop_seed: int
    input_path: Path
    noise_path: Path
    output_mix_path: Path
    output_noise_path: Path
    metadata_path: Path


def rms(x: np.ndarray) -> float:
    """Return root mean square amplitude."""
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64)) + EPS))


def power(x: np.ndarray) -> float:
    """Return mean squared power."""
    return float(np.mean(np.square(x, dtype=np.float64)))


def actual_snr_db(speech: np.ndarray, noise: np.ndarray) -> float:
    """Compute SNR in dB using mean squared power."""
    speech_power = power(speech)
    noise_power = power(noise)
    if noise_power <= EPS:
        return math.inf
    return 10.0 * math.log10((speech_power + EPS) / (noise_power + EPS))


def scale_noise_to_snr(
    speech: np.ndarray,
    noise: np.ndarray,
    snr_db: float,
) -> tuple[np.ndarray, float, float]:
    """Scale noise to the requested SNR relative to speech.

    Returns the scaled noise, the scalar gain applied to the noise, and the
    measured SNR after scaling.
    """
    speech_power = power(speech)
    noise_power = power(noise)
    if noise_power <= EPS:
        raise ValueError("Selected noise segment is silent; cannot scale to SNR.")

    scale = math.sqrt((speech_power + EPS) / (noise_power * (10.0 ** (snr_db / 10.0))))
    noise_scaled = noise * scale
    return noise_scaled, scale, actual_snr_db(speech, noise_scaled)


def prepare_noise_segment(
    noise: np.ndarray,
    target_length: int,
    rng: np.random.Generator,
    short_policy: str,
    long_policy: str,
) -> NoiseSegment:
    """Crop, loop, or pad a noise array to exactly target_length samples."""
    if target_length <= 0:
        raise ValueError("target_length must be positive.")
    if len(noise) == 0:
        raise ValueError("Noise file is empty.")

    if len(noise) < target_length:
        if short_policy == "loop":
            repeats = int(math.ceil(target_length / len(noise)))
            segment = np.tile(noise, repeats)[:target_length]
            return NoiseSegment(segment, 0, target_length, True)
        if short_policy == "pad":
            segment = np.zeros(target_length, dtype=noise.dtype)
            segment[: len(noise)] = noise
            return NoiseSegment(segment, 0, len(noise), False)
        raise ValueError(f"Unknown short noise policy: {short_policy}")

    if len(noise) > target_length:
        if long_policy == "random_crop":
            start = int(rng.integers(0, len(noise) - target_length + 1))
        elif long_policy == "start_crop":
            start = 0
        else:
            raise ValueError(f"Unknown long noise policy: {long_policy}")
        end = start + target_length
        return NoiseSegment(noise[start:end], start, end, False)

    return NoiseSegment(noise, 0, target_length, False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Libri2Mix-derived dataset with added factory noise."
    )
    parser.add_argument("--librimix-root", required=True, type=Path)
    parser.add_argument("--noise-dir", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--sample-rate", required=True, type=int, choices=[8000, 16000])
    parser.add_argument("--mode", required=True, choices=["min", "max"])
    parser.add_argument(
        "--splits",
        required=True,
        nargs="+",
        choices=["train-100", "train-360", "dev", "test"],
    )
    parser.add_argument("--input-type", default="mix_clean", choices=["mix_clean", "mix_both"])
    parser.add_argument("--snr-min", type=float)
    parser.add_argument("--snr-max", type=float)
    parser.add_argument("--snr-list", type=float, nargs="+")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--noise-short-policy", default="loop", choices=["loop", "pad"])
    parser.add_argument(
        "--noise-long-policy", default="random_crop", choices=["random_crop", "start_crop"]
    )
    parser.add_argument("--normalize", default="peak", choices=["none", "peak"])
    parser.add_argument("--clip-threshold", type=float, default=0.99)
    parser.add_argument("--output-name", default="mix_factory")
    return parser.parse_args()


def wav_folder(sample_rate: int) -> str:
    return "wav16k" if sample_rate == 16000 else "wav8k"


def collect_audio_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in AUDIO_EXTENSIONS)


def collect_input_wavs(args: argparse.Namespace, split: str) -> list[Path]:
    input_dir = (
        args.librimix_root
        / wav_folder(args.sample_rate)
        / args.mode
        / split
        / args.input_type
    )
    if not input_dir.is_dir():
        raise FileNotFoundError(
            f"Input directory does not exist: {input_dir}\n"
            "Check --librimix-root, --sample-rate, --mode, --splits, and --input-type."
        )
    wavs = sorted(input_dir.glob("*.wav"))
    if not wavs:
        raise FileNotFoundError(f"No .wav files found in input directory: {input_dir}")
    if args.limit is not None:
        wavs = wavs[: args.limit]
    return wavs


def read_audio_mono(path: Path, expected_sample_rate: int) -> np.ndarray:
    audio, sample_rate = sf.read(path, dtype="float32", always_2d=False)
    if sample_rate != expected_sample_rate:
        raise ValueError(
            f"Sample-rate mismatch for {path}: expected {expected_sample_rate}, got {sample_rate}. "
            "Resampling is not implemented in v1; provide matching-rate audio."
        )
    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)
    return np.asarray(audio, dtype=np.float32)


def format_snr_value(snr_db: float) -> str:
    if float(snr_db).is_integer():
        return str(int(snr_db))
    return (f"{snr_db:g}").replace("-", "neg_").replace(".", "p")


def snr_folder_name(snr_db: float) -> str:
    value = format_snr_value(snr_db)
    if not str(value).startswith("neg_"):
        return f"snr_{value}"
    return f"snr_-{str(value).removeprefix('neg_')}"


def output_paths_for(
    args: argparse.Namespace,
    split: str,
    input_path: Path,
    snr_db: float,
    fixed_snr_mode: bool,
) -> tuple[Path, Path, Path]:
    split_root = args.output_root / wav_folder(args.sample_rate) / args.mode / split
    if fixed_snr_mode:
        split_root = split_root / snr_folder_name(snr_db)

    output_mix_path = split_root / args.output_name / input_path.name
    output_noise_path = split_root / "noise_factory" / input_path.name
    metadata_path = split_root / "metadata" / "metadata_factory.csv"
    return output_mix_path, output_noise_path, metadata_path


def choose_snr(args: argparse.Namespace, rng: np.random.Generator) -> float:
    if args.snr_list is not None:
        raise RuntimeError("choose_snr is only used in random SNR mode.")
    return float(rng.uniform(args.snr_min, args.snr_max))


def validate_args(args: argparse.Namespace) -> None:
    if not args.librimix_root.is_dir():
        raise FileNotFoundError(f"LibriMix root does not exist: {args.librimix_root}")
    if not args.noise_dir.is_dir():
        raise FileNotFoundError(f"Noise directory does not exist: {args.noise_dir}")
    if args.num_workers != 1:
        warnings.warn(
            "--num-workers is accepted for compatibility, but this v1 implementation runs "
            "single-process.",
            stacklevel=2,
        )
    if args.input_type == "mix_both":
        warnings.warn(
            "--input-type mix_both adds factory noise on top of Libri2Mix/WHAM noise.",
            stacklevel=2,
        )
    if args.snr_list is None:
        if args.snr_min is None or args.snr_max is None:
            raise ValueError("Random SNR mode requires both --snr-min and --snr-max.")
        if args.snr_min > args.snr_max:
            raise ValueError("--snr-min must be less than or equal to --snr-max.")
    else:
        if args.snr_min is not None or args.snr_max is not None:
            warnings.warn(
                "--snr-list was provided; --snr-min/--snr-max will be ignored.",
                stacklevel=2,
            )
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be positive when provided.")
    if args.clip_threshold <= 0:
        raise ValueError("--clip-threshold must be positive.")


def print_summary(args: argparse.Namespace, noise_files: list[Path]) -> None:
    if args.snr_list is None:
        snr_mode = f"random uniform [{args.snr_min}, {args.snr_max}] dB"
    else:
        snr_mode = "fixed list " + ", ".join(f"{snr:g}" for snr in args.snr_list) + " dB"
    print("LibriMix root:", args.librimix_root)
    print("Noise dir:", args.noise_dir)
    print("Output root:", args.output_root)
    print("Sample rate:", args.sample_rate)
    print("Mode:", args.mode)
    print("Splits:", " ".join(args.splits))
    print("Input type:", args.input_type)
    print("SNR mode:", snr_mode)
    print("Number of noise files:", len(noise_files))
    print("Seed:", args.seed)


def create_plan(
    args: argparse.Namespace,
    input_wavs: Iterable[Path],
    noise_files: list[Path],
    split: str,
    rng: np.random.Generator,
) -> list[OutputPlan]:
    plans: list[OutputPlan] = []
    fixed_snr_mode = args.snr_list is not None
    snrs = args.snr_list if fixed_snr_mode else [None]

    for snr_value in snrs:
        for input_path in input_wavs:
            snr_db = float(snr_value) if fixed_snr_mode else choose_snr(args, rng)
            noise_path = noise_files[int(rng.integers(0, len(noise_files)))]
            output_mix_path, output_noise_path, metadata_path = output_paths_for(
                args, split, input_path, snr_db, fixed_snr_mode
            )
            plans.append(
                OutputPlan(
                    split=split,
                    snr_db=snr_db,
                    crop_seed=int(rng.integers(0, 2**32 - 1)),
                    input_path=input_path,
                    noise_path=noise_path,
                    output_mix_path=output_mix_path,
                    output_noise_path=output_noise_path,
                    metadata_path=metadata_path,
                )
            )
    return plans


def dry_run(plans: list[OutputPlan]) -> None:
    preview_count = min(10, len(plans))
    print(f"Dry run: showing {preview_count} of {len(plans)} planned mixtures.")
    for plan in plans[:preview_count]:
        print(
            f"input={plan.input_path} | noise={plan.noise_path} | "
            f"target_snr={plan.snr_db:g} | output={plan.output_mix_path}"
        )


def normalize_if_needed(
    mixture: np.ndarray,
    noise_scaled: np.ndarray,
    normalize: str,
    clip_threshold: float,
) -> tuple[np.ndarray, np.ndarray, bool, float, float]:
    peak_before = float(np.max(np.abs(mixture))) if len(mixture) else 0.0
    was_normalized = False
    gain = 1.0

    if normalize == "peak":
        if peak_before > clip_threshold:
            gain = clip_threshold / (peak_before + EPS)
            mixture = mixture * gain
            noise_scaled = noise_scaled * gain
            was_normalized = True
    elif peak_before > 1.0:
        warnings.warn(
            f"Output mixture peak {peak_before:.6f} exceeds 1.0 and --normalize none was used.",
            stacklevel=2,
        )

    return mixture, noise_scaled, was_normalized, peak_before, gain


def ensure_output_dirs(plans: Iterable[OutputPlan]) -> None:
    for plan in plans:
        plan.output_mix_path.parent.mkdir(parents=True, exist_ok=True)
        plan.output_noise_path.parent.mkdir(parents=True, exist_ok=True)
        plan.metadata_path.parent.mkdir(parents=True, exist_ok=True)


def process_plan(args: argparse.Namespace, plan: OutputPlan) -> dict[str, object]:
    speech = read_audio_mono(plan.input_path, args.sample_rate)
    noise = read_audio_mono(plan.noise_path, args.sample_rate)
    segment = prepare_noise_segment(
        noise,
        len(speech),
        np.random.default_rng(plan.crop_seed),
        args.noise_short_policy,
        args.noise_long_policy,
    )
    noise_scaled, noise_scale, measured_snr = scale_noise_to_snr(
        speech, segment.samples, plan.snr_db
    )
    mixture = speech + noise_scaled
    mixture, noise_scaled, was_normalized, peak_before, normalization_gain = (
        normalize_if_needed(
            mixture,
            noise_scaled,
            args.normalize,
            args.clip_threshold,
        )
    )

    sf.write(plan.output_mix_path, mixture.astype(np.float32), args.sample_rate, subtype="FLOAT")
    sf.write(
        plan.output_noise_path,
        noise_scaled.astype(np.float32),
        args.sample_rate,
        subtype="FLOAT",
    )

    return {
        "utt_id": plan.input_path.stem,
        "split": plan.split,
        "sample_rate": args.sample_rate,
        "mode": args.mode,
        "input_type": args.input_type,
        "input_mix_path": str(plan.input_path),
        "output_mix_path": str(plan.output_mix_path),
        "output_noise_path": str(plan.output_noise_path),
        "factory_noise_path": str(plan.noise_path),
        "target_snr_db": f"{plan.snr_db:.10g}",
        "actual_snr_db": f"{measured_snr:.10g}",
        "noise_start_sample": segment.start_sample,
        "noise_end_sample": segment.end_sample,
        "noise_scale": f"{noise_scale:.10g}",
        "noise_short_policy": args.noise_short_policy,
        "noise_long_policy": args.noise_long_policy,
        "normalize": args.normalize,
        "was_normalized": was_normalized,
        "peak_before_normalization": f"{peak_before:.10g}",
        "normalization_gain": f"{normalization_gain:.10g}",
        "noise_was_looped": segment.was_looped,
        "seed": args.seed,
    }


def write_metadata(metadata_path: Path, rows: list[dict[str, object]]) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=METADATA_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def run(args: argparse.Namespace) -> None:
    validate_args(args)
    noise_files = collect_audio_files(args.noise_dir)
    if not noise_files:
        raise FileNotFoundError(
            f"No supported noise files found under {args.noise_dir}. "
            "Expected recursively collected .wav or .flac files."
        )

    all_input_wavs = {split: collect_input_wavs(args, split) for split in args.splits}
    print_summary(args, noise_files)

    rng = np.random.default_rng(args.seed)
    plans: list[OutputPlan] = []
    for split, input_wavs in all_input_wavs.items():
        plans.extend(create_plan(args, input_wavs, noise_files, split, rng))

    if args.dry_run:
        dry_run(plans)
        return

    ensure_output_dirs(plans)
    rows_by_metadata: dict[Path, list[dict[str, object]]] = {}
    for plan in tqdm(plans, desc="Adding factory noise", unit="file"):
        row = process_plan(args, plan)
        rows_by_metadata.setdefault(plan.metadata_path, []).append(row)

    for metadata_path, rows in rows_by_metadata.items():
        write_metadata(metadata_path, rows)

    print(f"Done. Generated {len(plans)} mixtures under {args.output_root}")


def main() -> int:
    args = parse_args()
    try:
        run(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

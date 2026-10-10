"""audio_dither.py
Multi-band spectral phase dithering and harmonic distortion engine
for WebAudio / PCM stream protection against acoustic device fingerprinting.
"""

import math
import random
from typing import List


def apply_spectral_audio_dither(
    pcm_samples: List[float], sample_rate: int = 44100, dither_intensity: float = 1.0
) -> List[float]:
    """
    Applies frequency-dependent phase dither and micro-harmonic distortion
    to raw PCM float arrays, masking hardware soundcard signatures.

    Args:
        pcm_samples: List of PCM samples as floats in range [-1.0, 1.0]
        sample_rate: Sample rate in Hz (default: 44100)
        dither_intensity: Intensity scale factor (0.0-1.0)

    Returns:
        List of dithered PCM samples
    """
    dithered_samples = []
    dither_intensity = max(0.0, min(1.0, dither_intensity))

    for i, sample in enumerate(pcm_samples):
        # Generate multi-band spectral dither noise profile
        # Different frequency bands get different dither amounts
        frequency_modulation = math.sin(2 * math.pi * 1000 * (i / sample_rate))

        # Sub-band dither (affects different frequency bands)
        bass_dither = ((random.random() * 2.0 - 1.0) * 5e-7) * dither_intensity
        mid_dither = ((random.random() * 2.0 - 1.0) * 3e-7) * dither_intensity
        treble_dither = ((random.random() * 2.0 - 1.0) * 1e-6) * dither_intensity

        # Combine dither components with frequency modulation
        spectral_noise = (
            bass_dither * (1.0 + 0.1 * frequency_modulation)
            + mid_dither * (1.0 + 0.2 * frequency_modulation)
            + treble_dither * (1.0 + 0.3 * frequency_modulation)
        )

        dithered_sample = sample + spectral_noise

        # Enforce strict signal saturation rails [-1.0, 1.0]
        if dithered_sample > 1.0:
            dithered_sample = 1.0
        elif dithered_sample < -1.0:
            dithered_sample = -1.0

        dithered_samples.append(dithered_sample)

    return dithered_samples


def apply_phase_dither(
    pcm_samples: List[float], phase_shift: float = 0.1
) -> List[float]:
    """
    Applies phase dithering to PCM stream by introducing subtle timing variations.
    Disrupts acoustic fingerprinting based on timing correlations.

    Args:
        pcm_samples: List of PCM samples
        phase_shift: Phase shift magnitude (0.0-0.5, default: 0.1)

    Returns:
        Phase-dithered PCM samples
    """
    phase_shift = max(0.0, min(0.5, phase_shift))
    dithered_samples = []

    for i, sample in enumerate(pcm_samples):
        # Apply sinusoidal phase modulation
        phase_modulation = math.sin(2 * math.pi * 50 * i / 44100) * phase_shift
        dithered_samples.append(sample * (1.0 + phase_modulation))

    return dithered_samples


def apply_harmonic_distortion(
    pcm_samples: List[float], distortion_amount: float = 0.05
) -> List[float]:
    """
    Applies subtle harmonic distortion to mask hardware amplifier signatures.
    Uses soft clipping to preserve audio quality while defeating fingerprinting.

    Args:
        pcm_samples: List of PCM samples
        distortion_amount: Distortion intensity (0.0-0.1)

    Returns:
        Distorted PCM samples
    """
    distortion_amount = max(0.0, min(0.1, distortion_amount))
    distorted_samples = []

    for sample in pcm_samples:
        # Soft clipping transfer function
        # y = (3/2) * x * (1 - (x^2)/3)  for |x| <= 1
        if abs(sample) < 1.0:
            distorted = sample * (1.0 + distortion_amount * (1.0 - (sample * sample) / 3.0))
        else:
            # Hard limit beyond saturation
            distorted = 1.0 if sample > 0 else -1.0

        distorted_samples.append(max(-1.0, min(1.0, distorted)))

    return distorted_samples


def create_acoustic_fingerprint_mask(
    sample_rate: int = 44100, duration_seconds: float = 1.0
) -> List[float]:
    """
    Generates a masking signal designed to disrupt acoustic fingerprinting algorithms.
    Creates subtle frequency-dependent noise that preserves audio quality.

    Args:
        sample_rate: Sample rate in Hz
        duration_seconds: Duration of mask signal

    Returns:
        List of PCM samples representing the mask signal
    """
    num_samples = int(sample_rate * duration_seconds)
    mask_samples = []

    for i in range(num_samples):
        # Multi-frequency noise components
        t = i / sample_rate
        noise = (
            0.001 * math.sin(2 * math.pi * 237.5 * t)  # Sub-audible component 1
            + 0.001 * math.sin(2 * math.pi * 312.5 * t)  # Sub-audible component 2
            + 0.0005 * (random.random() - 0.5)  # White noise floor
        )
        mask_samples.append(max(-1.0, min(1.0, noise)))

    return mask_samples

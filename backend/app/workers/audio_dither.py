"""
audio_dither.py
Multi-band spectral phase dithering and harmonic distortion engine
for WebAudio / PCM stream protection against acoustic device fingerprinting.
"""

import math
import random
from typing import List
import logging

logger = logging.getLogger(__name__)


class SpectralAudioDitherEngine:
    """
    Applies frequency-dependent phase dither and micro-harmonic distortion
    to audio streams to neutralize hardware acoustic fingerprinting.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        dither_intensity: float = 1e-6,
        enabled: bool = True,
    ):
        """
        Initialize the spectral audio dither engine.

        Args:
            sample_rate: Audio sample rate in Hz (default: 44100)
            dither_intensity: Dither noise magnitude (default: 1e-6)
            enabled: Enable/disable dithering (default: True)
        """
        self.sample_rate = sample_rate
        self.dither_intensity = dither_intensity
        self.enabled = enabled
        self.sample_counter = 0

    def apply_spectral_dither(
        self, pcm_samples: List[float]
    ) -> List[float]:
        """
        Applies frequency-dependent phase dither and micro-harmonic distortion
        to raw PCM float arrays, masking hardware soundcard signatures.

        Args:
            pcm_samples: List of PCM float samples in range [-1.0, 1.0]

        Returns:
            Dithered PCM samples
        """
        if not self.enabled or not pcm_samples:
            return pcm_samples

        dithered_samples: List[float] = []

        for i, sample in enumerate(pcm_samples):
            # Generate multi-band spectral dither noise profile
            # Use multiple frequency bands to mask device-specific resonances

            # Primary dither band (1kHz)
            frequency_modulation_1 = math.sin(
                2 * math.pi * 1000 * ((self.sample_counter + i) / self.sample_rate)
            )

            # Secondary dither band (3kHz)
            frequency_modulation_2 = math.sin(
                2 * math.pi * 3000 * ((self.sample_counter + i) / self.sample_rate)
            )

            # Tertiary dither band (7kHz)
            frequency_modulation_3 = math.sin(
                2 * math.pi * 7000 * ((self.sample_counter + i) / self.sample_rate)
            )

            # Combined spectral noise from multiple bands
            spectral_noise = (
                (
                    (random.random() * 2.0 - 1.0) * self.dither_intensity
                    * (1.0 + 0.2 * frequency_modulation_1)
                )
                + (
                    (random.random() * 2.0 - 1.0) * self.dither_intensity * 0.5
                    * (1.0 + 0.15 * frequency_modulation_2)
                )
                + (
                    (random.random() * 2.0 - 1.0) * self.dither_intensity * 0.25
                    * (1.0 + 0.1 * frequency_modulation_3)
                )
            ) / 3.0  # Normalize combined noise

            # Apply dither
            dithered_sample = sample + spectral_noise

            # Enforce strict signal saturation rails [-1.0, 1.0]
            if dithered_sample > 1.0:
                dithered_sample = 1.0
            elif dithered_sample < -1.0:
                dithered_sample = -1.0

            dithered_samples.append(dithered_sample)

        self.sample_counter += len(pcm_samples)
        return dithered_samples

    def apply_phase_randomization(
        self, pcm_samples: List[float], phase_shift_deg: float = 5.0
    ) -> List[float]:
        """
        Apply phase randomization to audio samples to obscure harmonic content.

        Args:
            pcm_samples: List of PCM float samples
            phase_shift_deg: Maximum phase shift in degrees (default: 5.0)

        Returns:
            Phase-shifted PCM samples
        """
        if not self.enabled or not pcm_samples:
            return pcm_samples

        phase_shifted_samples: List[float] = []
        phase_shift_rad = math.radians(phase_shift_deg)

        for i, sample in enumerate(pcm_samples):
            # Generate random phase shift for this sample
            random_phase = (random.random() - 0.5) * phase_shift_rad

            # Apply phase shift via rotation in complex plane (simplified)
            # For a real signal, we approximate by slight amplitude modulation
            phase_factor = math.cos(random_phase)
            shifted_sample = sample * phase_factor

            phase_shifted_samples.append(shifted_sample)

        return phase_shifted_samples

    def set_enabled(self, enabled: bool) -> None:
        """
        Enable/disable audio dithering.

        Args:
            enabled: Enable or disable dithering
        """
        self.enabled = enabled

    def set_dither_intensity(self, intensity: float) -> None:
        """
        Set dither intensity.

        Args:
            intensity: Dither magnitude (recommended: 1e-7 to 1e-5)
        """
        self.dither_intensity = max(0, intensity)

    def get_config(self) -> dict:
        """
        Get current engine configuration.

        Returns:
            Configuration dictionary
        """
        return {
            "sample_rate": self.sample_rate,
            "dither_intensity": self.dither_intensity,
            "enabled": self.enabled,
        }


def apply_spectral_audio_dither(
    pcm_samples: List[float],
    sample_rate: int = 44100,
    dither_intensity: float = 1e-6,
) -> List[float]:
    """
    Utility function for quick spectral audio dithering.
    Creates a temporary engine and applies dithering.

    Args:
        pcm_samples: List of PCM float samples
        sample_rate: Audio sample rate in Hz
        dither_intensity: Dither noise magnitude

    Returns:
        Dithered PCM samples
    """
    engine = SpectralAudioDitherEngine(
        sample_rate=sample_rate,
        dither_intensity=dither_intensity,
        enabled=True,
    )
    return engine.apply_spectral_dither(pcm_samples)

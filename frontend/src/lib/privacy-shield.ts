/**
 * privacy-shield.ts
 * Frontend implementation of the PCG32 PRNG and deterministic canvas/kinematic dither engine
 * Inspired by Project FF-Shield core specifications for privacy protection and anti-fingerprinting.
 */

/**
 * PCG32 Pseudorandom Number Generator
 * A lightweight, deterministic PRNG for reproducible privacy noise injection.
 */
export class PCG32Generator {
  private state: bigint;
  private inc: bigint;

  /**
   * Initialize PCG32 with a 32-bit seed.
   * @param seed - Initial seed value (default: 0x4f35219a)
   */
  constructor(seed: number = 0x4f35219a) {
    this.state = BigInt(seed);
    this.inc = (BigInt(seed) << 1n) | 1n;
    this.nextU32(); // Warm up the generator
  }

  /**
   * Generate next 32-bit unsigned integer.
   * @returns Random unsigned 32-bit integer
   */
  nextU32(): number {
    const oldState = this.state;
    this.state = oldState * 6364136223846793005n + this.inc;
    const xorshifted = Number(((oldState >> 18n) ^ oldState) >> 27n);
    const rot = Number(oldState >> 59n);
    return (xorshifted >>> rot) | (xorshifted << ((-rot) & 31));
  }

  /**
   * Generate next random float in range [0, 1).
   * @returns Random floating point value
   */
  nextFloat(): number {
    return (this.nextU32() >>> 0) / 0x100000000;
  }
}

/**
 * PrivacyShieldEngine
 * Core privacy engine implementing canvas dithering and kinematic noise injection.
 */
export class PrivacyShieldEngine {
  private prng: PCG32Generator;
  private enabled: boolean;
  private ditherIntensity: number;

  /**
   * Initialize the privacy shield engine.
   * @param seed - PRNG seed for deterministic reproducibility
   * @param enabled - Enable/disable privacy shield (default: true)
   * @param ditherIntensity - Intensity of canvas dithering (default: 1.0)
   */
  constructor(
    seed: number = 1337,
    enabled: boolean = true,
    ditherIntensity: number = 1.0
  ) {
    this.prng = new PCG32Generator(seed);
    this.enabled = enabled;
    this.ditherIntensity = Math.max(0, Math.min(1, ditherIntensity)); // Clamp to [0, 1]
  }

  /**
   * Applies low-order RGB bit dithering to HTML5 Canvas frame buffers
   * to defeat cross-site canvas fingerprinting without visual degradation.
   * Uses ±1 bit shifts on R, G, B channels.
   *
   * @param ctx - CanvasRenderingContext2D for frame manipulation
   * @param width - Canvas width in pixels
   * @param height - Canvas height in pixels
   */
  applyCanvasDither(
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number
  ): void {
    if (!this.enabled || this.ditherIntensity === 0) return;

    try {
      const imageData = ctx.getImageData(0, 0, width, height);
      const pixels = imageData.data;

      // Process RGBA pixels in 4-byte chunks
      for (let i = 0; i < pixels.length; i += 4) {
        if (i + 3 >= pixels.length) break;

        // Generate deterministic dither values
        const noise = this.prng.nextU32();
        const shiftMask = (noise & 0x01) * this.ditherIntensity; // Scale by intensity

        // Apply ±1 bit shift to R, G, B channels
        // This is imperceptible to human vision but breaks canvas fingerprinting
        pixels[i] = Math.min(255, Math.max(0, pixels[i] ^ (shiftMask | 0))); // R
        pixels[i + 1] = Math.min(255, Math.max(0, pixels[i + 1] ^ (shiftMask | 0))); // G
        pixels[i + 2] = Math.min(255, Math.max(0, pixels[i + 2] ^ (shiftMask | 0))); // B
        // Alpha channel (i + 3) remains untouched to avoid clipping artifacts
      }

      ctx.putImageData(imageData, 0, 0);
    } catch (error) {
      // Handle cross-origin or tainted canvas restrictions gracefully
      console.warn(
        "PrivacyShield: Canvas readback restricted (likely cross-origin or tainted).",
        error
      );
    }
  }

  /**
   * Injects zero-mean Gaussian differential privacy noise into interaction kinematics
   * (e.g., mouse velocities, touch streams) to protect against behavioral re-identification.
   *
   * Uses Box-Muller transform to generate Gaussian-distributed noise.
   * Sensitivity parameter controls the magnitude of injected noise.
   *
   * @param value - Original kinematic value (e.g., mouse velocity)
   * @param sensitivity - DP sensitivity parameter (default: 4.2)
   * @param epsilon - Privacy budget (default: 0.1, lower = more privacy but more noise)
   * @returns Noisy value with differential privacy guarantees
   */
  applyKinematicNoise(
    value: number,
    sensitivity: number = 4.2,
    epsilon: number = 0.1
  ): number {
    if (!this.enabled || epsilon <= 0) return value;

    // Calibrate Gaussian noise scale sigma based on DP formula
    // sigma = (sensitivity * sqrt(2 * ln(2))) / epsilon
    const sigma = (sensitivity * Math.sqrt(2 * Math.LN2)) / epsilon;

    // Box-Muller transform using PCG32 to generate Gaussian random variable
    const u1 = Math.max(1e-7, this.prng.nextFloat());
    const u2 = this.prng.nextFloat();
    const gaussianNoise =
      Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);

    // Scale noise and add to original value
    // Divide by 1000 to keep noise magnitude reasonable
    return value + gaussianNoise * (sigma / 1000.0);
  }

  /**
   * Apply differential privacy noise to touch/pointer coordinates.
   * @param x - Original X coordinate
   * @param y - Original Y coordinate
   * @param sensitivity - DP sensitivity (default: 2.1)
   * @param epsilon - Privacy budget (default: 0.1)
   * @returns Tuple of [noisyX, noisyY]
   */
  applyPointerNoise(
    x: number,
    y: number,
    sensitivity: number = 2.1,
    epsilon: number = 0.1
  ): [number, number] {
    return [
      this.applyKinematicNoise(x, sensitivity, epsilon),
      this.applyKinematicNoise(y, sensitivity, epsilon),
    ];
  }

  /**
   * Toggle privacy shield on/off.
   * @param enabled - Enable or disable the shield
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  /**
   * Set dither intensity (0.0 = no dither, 1.0 = full dither).
   * @param intensity - Dither intensity value [0, 1]
   */
  setDitherIntensity(intensity: number): void {
    this.ditherIntensity = Math.max(0, Math.min(1, intensity));
  }
}

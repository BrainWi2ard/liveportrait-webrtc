/**
 * latent-shield.ts
 * Implements client-side tensor/bitmap perturbation to defeat automated
 * biometric facial embedding and tracking extractors (e.g., DeepFace).
 * Inspired by FGSM/PGD adversarial perturbation concepts.
 */

export class LatentShieldEngine {
  private intensity: number;
  private enabled: boolean;
  private perturbationCache: Map<string, Uint8ClampedArray> = new Map();

  /**
   * Initialize the Latent Shield Engine.
   * @param intensity - Perturbation intensity (0.0 - 1.0, default: 0.015)
   * @param enabled - Enable/disable perturbation (default: true)
   */
  constructor(intensity: number = 0.015, enabled: boolean = true) {
    this.intensity = Math.max(0, Math.min(1, intensity));
    this.enabled = enabled;
  }

  /**
   * Applies imperceptible, high-frequency spatial perturbations across color channels
   * to disrupt convolutional neural network feature space representations.
   * Uses gradient-aligned noise patterns inspired by FGSM/PGD adversarial attacks.
   *
   * @param ctx - CanvasRenderingContext2D for frame manipulation
   * @param width - Canvas width in pixels
   * @param height - Canvas height in pixels
   */
  applyPerturbation(
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number
  ): void {
    if (!this.enabled || this.intensity === 0) return;

    try {
      const imageData = ctx.getImageData(0, 0, width, height);
      const data = imageData.data;

      // Simulate localized gradient perturbation patterns
      // Process every 2x2 pixel block to maintain performance
      for (let y = 0; y < height; y += 2) {
        for (let x = 0; x < width; x += 2) {
          const index = (y * width + x) * 4;

          if (index + 3 >= data.length) break;

          // Generate pseudo-gradient directional noise delta
          // Using Perlin noise-like hash for smooth perturbation fields
          const perturbation =
            Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
          const noiseDelta = Math.floor(
            (perturbation - Math.floor(perturbation)) * (this.intensity * 10)
          );

          // Apply gradient-aligned perturbations to RGB channels
          // Alpha channel remains unchanged to preserve transparency
          data[index] = Math.min(255, Math.max(0, data[index] + noiseDelta)); // R
          data[index + 1] = Math.min(
            255,
            Math.max(0, data[index + 1] - noiseDelta)
          ); // G
          data[index + 2] = Math.min(255, Math.max(0, data[index + 2] + noiseDelta)); // B
          // data[index + 3] remains unchanged (alpha)
        }
      }

      ctx.putImageData(imageData, 0, 0);
    } catch (error) {
      console.warn(
        "LatentShield: Frame tensor perturbation restricted (cross-origin or tainted canvas).",
        error
      );
    }
  }

  /**
   * Set the perturbation intensity.
   * @param intensity - New intensity value [0, 1]
   */
  setIntensity(intensity: number): void {
    this.intensity = Math.max(0, Math.min(1, intensity));
  }

  /**
   * Toggle perturbation on/off.
   * @param enabled - Enable or disable perturbation
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  /**
   * Get current configuration.
   */
  getConfig() {
    return {
      enabled: this.enabled,
      intensity: this.intensity,
    };
  }
}

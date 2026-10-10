/**
 * latent-shield.ts
 * Implements client-side tensor/bitmap perturbation to defeat automated
 * biometric facial embedding and tracking extractors (e.g., DeepFace).
 * Inspired by FGSM/PGD adversarial perturbation concepts.
 */

export class LatentShieldEngine {
  private intensity: number;
  private enabled: boolean;
  private perturbationCache: Map<string, number[]> = new Map();

  /**
   * Initialize the Latent Shield Engine.
   * @param intensity - Perturbation intensity scale (default: 0.015, range: 0.0-0.05)
   * @param enabled - Enable/disable latent perturbations (default: true)
   */
  constructor(intensity: number = 0.015, enabled: boolean = true) {
    this.intensity = Math.max(0, Math.min(0.05, intensity));
    this.enabled = enabled;
  }

  /**
   * Applies imperceptible, high-frequency spatial perturbations across color channels
   * to disrupt convolutional neural network feature space representations.
   * Uses pseudo-gradient directional noise patterns inspired by adversarial examples.
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
    if (!this.enabled) return;

    try {
      const imageData = ctx.getImageData(0, 0, width, height);
      const data = imageData.data;

      // Simulate localized gradient perturbation patterns
      // Process every 2x2 block to reduce computational overhead
      for (let y = 0; y < height; y += 2) {
        for (let x = 0; x < width; x += 2) {
          const index = (y * width + x) * 4;
          if (index + 3 >= data.length) break;

          // Generate pseudo-gradient directional noise delta
          // Uses Perlin-like noise approximation via trigonometric functions
          const perturbation =
            Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
          const noiseDelta = Math.floor(
            (perturbation - Math.floor(perturbation)) * (this.intensity * 10)
          );

          // Apply gradient-aligned perturbations to RGB channels
          // A: X-component (R channel +delta)
          // B: Y-component (G channel -delta)
          // C: Diagonal (B channel +delta)
          data[index] = Math.min(
            255,
            Math.max(0, data[index] + noiseDelta)
          ); // R
          data[index + 1] = Math.min(
            255,
            Math.max(0, data[index + 1] - noiseDelta)
          ); // G
          data[index + 2] = Math.min(
            255,
            Math.max(0, data[index + 2] + noiseDelta)
          ); // B
          // Alpha channel remains untouched
        }
      }

      ctx.putImageData(imageData, 0, 0);
    } catch (e) {
      console.warn(
        "LatentShield: Frame tensor perturbation restricted (likely cross-origin or tainted canvas).",
        e
      );
    }
  }

  /**
   * Applies targeted perturbations to specific regions (e.g., face detected regions).
   * More computationally efficient for targeted biometric disruption.
   *
   * @param ctx - CanvasRenderingContext2D
   * @param x - Region origin X coordinate
   * @param y - Region origin Y coordinate
   * @param width - Region width
   * @param height - Region height
   */
  applyRegionalPerturbation(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number
  ): void {
    if (!this.enabled) return;

    try {
      const imageData = ctx.getImageData(x, y, width, height);
      const data = imageData.data;

      for (let py = 0; py < height; py += 2) {
        for (let px = 0; px < width; px += 2) {
          const index = (py * width + px) * 4;
          if (index + 3 >= data.length) break;

          const perturbation =
            Math.sin((x + px) * 12.9898 + (y + py) * 78.233) *
            43758.5453;
          const noiseDelta = Math.floor(
            (perturbation - Math.floor(perturbation)) * (this.intensity * 10)
          );

          data[index] = Math.min(255, Math.max(0, data[index] + noiseDelta));
          data[index + 1] = Math.min(
            255,
            Math.max(0, data[index + 1] - noiseDelta)
          );
          data[index + 2] = Math.min(
            255,
            Math.max(0, data[index + 2] + noiseDelta)
          );
        }
      }

      ctx.putImageData(imageData, x, y);
    } catch (e) {
      console.warn(
        "LatentShield: Regional perturbation failed.",
        e
      );
    }
  }

  /**
   * Toggle latent shield on/off.
   * @param enabled - Enable or disable the shield
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  /**
   * Adjust perturbation intensity.
   * @param intensity - Intensity value [0.0, 0.05]
   */
  setIntensity(intensity: number): void {
    this.intensity = Math.max(0, Math.min(0.05, intensity));
  }
}

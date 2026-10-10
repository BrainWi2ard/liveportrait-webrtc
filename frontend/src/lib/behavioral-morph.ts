/**
 * behavioral-morph.ts
 * Simulates non-stationary human motor control properties (fatigue, attention decay,
 * micro-tremors) using a Markov state machine.
 * Defeats statistical behavioral classifiers looking for stationary bot patterns.
 */

export type FatigueState = "ALERT" | "FOCUSED" | "FATIGUED" | "DISTRACTED";

export interface BehavioralState {
  state: FatigueState;
  timeOnDevice: number;
  tremorScale: number;
  attentionDrift: number;
}

export class BehavioralMorphEngine {
  private currentState: FatigueState = "ALERT";
  private timeOnDeviceSec: number = 0;
  private tremorScale: number = 1.0;
  private attentionDrift: number = 0.0;
  private stateUpdateInterval: NodeJS.Timeout | null = null;
  private enabled: boolean = true;

  constructor(enabled: boolean = true) {
    this.enabled = enabled;

    // Initialize state machine timer (only in browser environment)
    if (typeof window !== "undefined") {
      this.stateUpdateInterval = setInterval(() => {
        this.timeOnDeviceSec += 1;
        this.updateMarkovState();
      }, 1000);
    }
  }

  /**
   * Update Markov state based on session duration and simulated attention.
   * Transitions between states with realistic human-like patterns.
   */
  private updateMarkovState(): void {
    if (!this.enabled) return;

    // Simulate attention drift (random walk)
    this.attentionDrift = Math.max(
      -1.0,
      Math.min(1.0, this.attentionDrift + (Math.random() - 0.5) * 0.1)
    );

    // State transitions based on time-on-device
    if (this.timeOnDeviceSec > 600) {
      // 10+ minutes: High fatigue
      this.currentState = "FATIGUED";
      this.tremorScale = 2.4;
    } else if (this.timeOnDeviceSec > 300) {
      // 5-10 minutes: Distraction sets in
      this.currentState = "DISTRACTED";
      this.tremorScale = 1.8;
    } else if (this.timeOnDeviceSec > 60) {
      // 1-5 minutes: Peak focus
      this.currentState = "FOCUSED";
      this.tremorScale = 1.2;
    } else {
      // 0-1 minute: Alert state
      this.currentState = "ALERT";
      this.tremorScale = 1.0;
    }
  }

  /**
   * Modulates input coordinates with state-dependent kinematic tremors.
   * Simulates natural human motor control variability.
   *
   * @param x - Original X coordinate
   * @param y - Original Y coordinate
   * @returns Morphed coordinates with tremor and attention-based drift
   */
  morphKinematics(x: number, y: number): { x: number; y: number } {
    if (!this.enabled) return { x, y };

    // Generate state-dependent tremor magnitude
    const baseNoise = (Math.random() - 0.5) * 2.0; // Range: [-1, 1]
    const stateMultiplier = this.tremorScale;
    const attentionFactor = 1.0 + this.attentionDrift * 0.5; // Range: [0.5, 1.5]

    const randomTremorX = baseNoise * stateMultiplier * attentionFactor;
    const randomTremorY = baseNoise * stateMultiplier * attentionFactor * 0.8; // Slight Y bias

    return {
      x: x + randomTremorX,
      y: y + randomTremorY,
    };
  }

  /**
   * Calculate interaction latency based on current state.
   * Simulates realistic human response times.
   *
   * @returns Latency in milliseconds
   */
  getInteractionLatency(): number {
    if (!this.enabled) return 0;

    let baseLatency = 0;
    switch (this.currentState) {
      case "ALERT":
        baseLatency = 150 + Math.random() * 50; // 150-200ms
        break;
      case "FOCUSED":
        baseLatency = 180 + Math.random() * 70; // 180-250ms
        break;
      case "DISTRACTED":
        baseLatency = 250 + Math.random() * 150; // 250-400ms
        break;
      case "FATIGUED":
        baseLatency = 350 + Math.random() * 200; // 350-550ms
        break;
    }
    return Math.round(baseLatency);
  }

  /**
   * Get current behavioral state information.
   */
  getStateInfo(): BehavioralState {
    return {
      state: this.currentState,
      timeOnDevice: this.timeOnDeviceSec,
      tremorScale: this.tremorScale,
      attentionDrift: this.attentionDrift,
    };
  }

  /**
   * Reset the session timer (e.g., on user interaction).
   */
  resetSession(): void {
    this.timeOnDeviceSec = 0;
    this.currentState = "ALERT";
    this.tremorScale = 1.0;
    this.attentionDrift = 0.0;
  }

  /**
   * Enable/disable behavioral morphing.
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  /**
   * Clean up timers and resources.
   */
  destroy(): void {
    if (this.stateUpdateInterval) {
      clearInterval(this.stateUpdateInterval);
      this.stateUpdateInterval = null;
    }
  }
}

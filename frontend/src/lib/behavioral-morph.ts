/**
 * behavioral-morph.ts
 * Simulates non-stationary human motor control properties (fatigue, attention decay,
 * micro-tremors) using a Markov chain state machine.
 * Defeats statistical behavioral classifiers looking for bot/automation patterns.
 */

export type FatigueState = "ALERT" | "FOCUSED" | "FATIGUED" | "DISTRACTED";

export interface StateInfo {
  state: FatigueState;
  timeOnDevice: number;
  tremorScale: number;
  focusDrift: number;
  latencyModulation: number;
}

/**
 * Markov-driven kinematic morphing engine.
 * Dynamically modulates mouse kinematics, pointer tremor frequencies,
 * and UI interaction latency profiles to defeat behavioral classifiers.
 */
export class BehavioralMorphEngine {
  private currentState: FatigueState = "ALERT";
  private timeOnDeviceSec: number = 0;
  private tremorScale: number = 1.0;
  private focusDrift: number = 0.0;
  private latencyModulation: number = 1.0;
  private stateTransitionTimer: number | null = null;
  private focusDriftAccumulator: number = 0;

  constructor() {
    // Start the Markov state machine update loop
    if (typeof window !== "undefined") {
      this.stateTransitionTimer = window.setInterval(() => {
        this.timeOnDeviceSec += 1;
        this.updateMarkovState();
        this.updateFocusDrift();
      }, 1000);
    }
  }

  /**
   * Update Markov state based on session duration.
   * Simulates realistic human fatigue/attention patterns.
   */
  private updateMarkovState(): void {
    // State transition probabilities based on time-on-device
    if (this.timeOnDeviceSec > 600) {
      this.currentState = "FATIGUED";
      this.tremorScale = 2.4;
      this.latencyModulation = 1.5;
    } else if (this.timeOnDeviceSec > 300) {
      this.currentState = "DISTRACTED";
      this.tremorScale = 1.8;
      this.latencyModulation = 1.25;
    } else if (this.timeOnDeviceSec > 60) {
      this.currentState = "FOCUSED";
      this.tremorScale = 1.2;
      this.latencyModulation = 1.0;
    } else {
      this.currentState = "ALERT";
      this.tremorScale = 1.0;
      this.latencyModulation = 0.95;
    }
  }

  /**
   * Simulate attention drift (looking away from screen, refocusing).
   * Creates realistic variation in mouse movement precision.
   */
  private updateFocusDrift(): void {
    this.focusDriftAccumulator += (Math.random() - 0.5) * 0.1;
    this.focusDrift = Math.sin(this.focusDriftAccumulator) * 0.2;
  }

  /**
   * Modulates input coordinates with state-dependent kinematic tremors.
   * Applies realistic human motor control variability.
   *
   * @param x - Original X coordinate
   * @param y - Original Y coordinate
   * @returns Morphed coordinates with tremor applied
   */
  morphKinematics(x: number, y: number): { x: number; y: number } {
    const randomTremorX = (Math.random() - 0.5) * this.tremorScale;
    const randomTremorY = (Math.random() - 0.5) * this.tremorScale;

    // Apply focus drift to reduce precision over time
    const driftedX = x + this.focusDrift * 5;
    const driftedY = y + this.focusDrift * 5;

    return {
      x: driftedX + randomTremorX,
      y: driftedY + randomTremorY,
    };
  }

  /**
   * Calculate reaction time delay with state-dependent modulation.
   * Simulates realistic human response latency.
   *
   * @param baseLatencyMs - Base reaction time (typically 200-400ms)
   * @returns Modulated latency in milliseconds
   */
  getReactionTimeDelay(baseLatencyMs: number = 250): number {
    // Add state-dependent jitter
    const jitter = (Math.random() - 0.5) * 50 * this.latencyModulation;
    return baseLatencyMs * this.latencyModulation + jitter;
  }

  /**
   * Get current state information for debugging/monitoring.
   * @returns Current behavioral state snapshot
   */
  getStateInfo(): StateInfo {
    return {
      state: this.currentState,
      timeOnDevice: this.timeOnDeviceSec,
      tremorScale: this.tremorScale,
      focusDrift: this.focusDrift,
      latencyModulation: this.latencyModulation,
    };
  }

  /**
   * Reset the behavioral engine (e.g., on new session).
   */
  reset(): void {
    this.currentState = "ALERT";
    this.timeOnDeviceSec = 0;
    this.tremorScale = 1.0;
    this.focusDrift = 0.0;
    this.latencyModulation = 1.0;
    this.focusDriftAccumulator = 0;
  }

  /**
   * Cleanup resources.
   */
  destroy(): void {
    if (this.stateTransitionTimer !== null) {
      clearInterval(this.stateTransitionTimer);
    }
  }
}

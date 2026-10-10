import { useCallback, useEffect, useRef, useState } from 'react';
import { PrivacyShieldEngine } from '@/lib/privacy-shield';

export type WebRTCStats = {
  fps: number;
  renderLatencyMs: number;
  audioVideoSyncDriftMs: number;
  packetJitterMs: number;
};

type SignalMessage =
  | { type: 'sdp_offer'; sdp: string; session_id: string; target_asset_id?: number | null }
  | { type: 'sdp_answer'; sdp: string; session_id: string }
  | { type: 'ice_candidate'; candidate: string; sdpMLineIndex?: number | null; sdpMid?: string | null; session_id: string }
  | { type: 'asset_switch'; target_asset_id: number; session_id: string }
  | { type: 'diagnostics_request'; session_id: string };

export class WebRTCClient {
  private peerConnection: RTCPeerConnection | null = null;
  private localStream: MediaStream | null = null;
  private remoteStream: MediaStream | null = null;
  private socket: WebSocket | null = null;
  private sessionId: string;
  private signalingUrl: string;
  private onStatsUpdate?: (stats: WebRTCStats) => void;
  private diagnosticsTimer: number | null = null;
  private privacyShield: PrivacyShieldEngine;
  private canvasContext: CanvasRenderingContext2D | null = null;
  private canvasElement: HTMLCanvasElement | null = null;

  constructor(sessionId: string, signalingUrl: string, onStatsUpdate?: (stats: WebRTCStats) => void) {
    this.sessionId = sessionId;
    this.signalingUrl = signalingUrl;
    this.onStatsUpdate = onStatsUpdate;
    // Initialize privacy shield with session-based seed
    const seedFromSessionId = parseInt(sessionId.substring(0, 8), 16) || 12345;
    this.privacyShield = new PrivacyShieldEngine(seedFromSessionId, true, 1.0);
  }

  async initLocalMedia(): Promise<MediaStream> {
    this.localStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'user',
      },
      audio: true,
    });

    return this.localStream;
  }

  connectSocket(): void {
    this.socket = new WebSocket(this.signalingUrl);

    this.socket.onopen = () => {
      console.log('WebSocket signaling connected');
      this.requestDiagnostics();
    };

    this.socket.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'sdp_answer') {
        this.handleAnswer(message.sdp);
      }

      if (message.type === 'diagnostics') {
        this.onStatsUpdate?.({
          fps: Number(message.fps ?? 30),
          renderLatencyMs: Number(message.render_latency_ms ?? 0),
          audioVideoSyncDriftMs: Number(message.audio_video_sync_drift_ms ?? 0),
          packetJitterMs: Number(message.packet_jitter_ms ?? 0),
        });
      }
    };

    this.socket.onerror = () => {
      console.warn('WebSocket connection error, retrying...');
      setTimeout(() => this.connectSocket(), 2000);
    };
  }

  createPeerConnection(): void {
    const configuration: RTCConfiguration = {
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    };

    this.peerConnection = new RTCPeerConnection(configuration);

    if (this.localStream) {
      this.localStream.getTracks().forEach((track) => {
        this.peerConnection?.addTrack(track, this.localStream!);
      });
    }

    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate && this.socket) {
        // Filter out local IP leaks (privacy protection)
        if (this.shouldFilterICECandidate(event.candidate)) {
          console.debug('PrivacyShield: Filtered local IP leak in ICE candidate');
          return;
        }

        const payload: SignalMessage = {
          type: 'ice_candidate',
          candidate: event.candidate.candidate,
          sdpMLineIndex: event.candidate.sdpMLineIndex,
          sdpMid: event.candidate.sdpMid ?? null,
          session_id: this.sessionId,
        };

        this.socket.send(JSON.stringify(payload));
      }
    };

    this.peerConnection.ontrack = (event) => {
      this.remoteStream = event.streams[0];
      console.log('Remote stream received', this.remoteStream);
    };
  }

  /**
   * Filter ICE candidates to prevent local IP leaks.
   * Blocks host candidates that expose internal network addresses.
   */
  private shouldFilterICECandidate(candidate: RTCIceCandidate): boolean {
    if (!candidate.candidate) return false;

    // Block private IP ranges to prevent local network disclosure
    const privateIPPatterns = [
      /\b(?:10|127|172|192|169|255)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/,
      /^(?:10|127|172|192|169|255)\./,
    ];

    return privateIPPatterns.some((pattern) => pattern.test(candidate.candidate));
  }

  /**
   * Process video frames through canvas dither to defeat fingerprinting.
   * Should be called during frame capture/export to the WebRTC stream.
   */
  processFrameDither(canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D): void {
    this.privacyShield.applyCanvasDither(ctx, canvas.width, canvas.height);
  }

  /**
   * Apply kinematic noise to protect against behavioral fingerprinting.
   * Use this when processing user interactions before sending to backend.
   */
  applyKinematicNoise(value: number, sensitivity?: number, epsilon?: number): number {
    return this.privacyShield.applyKinematicNoise(value, sensitivity, epsilon);
  }

  async startCall(): Promise<void> {
    if (!this.peerConnection) {
      this.createPeerConnection();
    }

    const offer = await this.peerConnection!.createOffer();
    await this.peerConnection!.setLocalDescription(offer);

    this.socket?.send(
      JSON.stringify({
        type: 'sdp_offer',
        sdp: offer.sdp,
        session_id: this.sessionId,
        target_asset_id: null,
      } as SignalMessage)
    );
  }

  async handleAnswer(sdp: string): Promise<void> {
    if (!this.peerConnection) return;
    const answer = new RTCSessionDescription({ sdp, type: 'answer' });
    await this.peerConnection.setRemoteDescription(answer);
  }

  requestDiagnostics(): void {
    this.diagnosticsTimer = window.setInterval(() => {
      this.socket?.send(
        JSON.stringify({
          type: 'diagnostics_request',
          session_id: this.sessionId,
        } satisfies SignalMessage)
      );
    }, 1000);
  }

  switchAsset(targetAssetId: number): void {
    this.socket?.send(
      JSON.stringify({
        type: 'asset_switch',
        target_asset_id: targetAssetId,
        session_id: this.sessionId,
      } satisfies SignalMessage)
    );
  }

  getLocalStream(): MediaStream | null {
    return this.localStream;
  }

  getRemoteStream(): MediaStream | null {
    return this.remoteStream;
  }

  getPrivacyShield(): PrivacyShieldEngine {
    return this.privacyShield;
  }

  close(): void {
    if (this.diagnosticsTimer) {
      clearInterval(this.diagnosticsTimer);
    }

    this.peerConnection?.close();
    this.socket?.close();
  }
}

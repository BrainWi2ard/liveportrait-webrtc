import { useCallback, useEffect, useRef, useState } from 'react';
import axios, { AxiosError } from 'axios';
import { WebRTCClient, WebRTCStats } from '@/lib/webrtc';

interface LivePortraitSession {
  sessionId: string;
  userId: string;
  encodedToken: string;
  expiresIn: number;
}

interface AssetSwitchPayload {
  type: 'swap_identity' | 'update_voice_pitch' | 'get_gpu_health';
  targetAssetId?: number;
  voicePitch?: number;
}

interface StreamedMetrics {
  fps: number;
  latency: number;
  drift: number;
  timestamp: number;
}

interface UseLivePortraitReturn {
  session: LivePortraitSession | null;
  stats: WebRTCStats | null;
  isConnecting: boolean;
  isConnected: boolean;
  error: string | null;
  initSession: (userId: string) => Promise<void>;
  switchAsset: (assetId: number) => void;
  getGPUHealth: () => void;
  updateVoicePitch: (pitch: number) => void;
  disconnect: () => void;
  metrics: StreamedMetrics | null;
}

export function useLivePortrait(signalingUrl: string): UseLivePortraitReturn {
  const [session, setSession] = useState<LivePortraitSession | null>(null);
  const [stats, setStats] = useState<WebRTCStats | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<StreamedMetrics | null>(null);

  const webrtcClientRef = useRef<WebRTCClient | null>(null);
  const streamReaderRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  // Initialize WebRTC session with Vercel AI SDK streaming
  const initSession = useCallback(
    async (userId: string) => {
      try {
        setIsConnecting(true);
        setError(null);

        // Call the AI session endpoint to get streaming session token
        const response = await axios.post(
          '/api/ai/session',
          { userId },
          { responseType: 'stream' }
        );

        let sessionData: LivePortraitSession | null = null;
        const decoder = new TextDecoder();
        let buffer = '';

        // Parse SSE stream from AI endpoint
        streamReaderRef.current = response.data.getReader();

        while (true) {
          const { done, value } = await streamReaderRef.current.read();

          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');

          for (let i = 0; i < lines.length - 1; i++) {
            const line = lines[i];
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.type === 'session_token') {
                  sessionData = {
                    sessionId: data.payload.sessionId,
                    userId: data.payload.userId,
                    encodedToken: data.encodedToken,
                    expiresIn: data.payload.expiresIn,
                  };
                  setSession(sessionData);
                } else if (data.type === 'orchestration_stream') {
                  console.log('Orchestration chunk:', data.chunk);
                }
              } catch (e) {
                console.error('Failed to parse SSE message:', e);
              }
            }
          }

          buffer = lines[lines.length - 1];
        }

        if (!sessionData) {
          throw new Error('Failed to initialize session');
        }

        // Initialize WebRTC client with privacy shield enabled
        webrtcClientRef.current = new WebRTCClient(
          sessionData.sessionId,
          signalingUrl,
          (webrtcStats: WebRTCStats) => {
            setStats(webrtcStats);
            setMetrics({
              fps: webrtcStats.fps,
              latency: webrtcStats.renderLatencyMs,
              drift: webrtcStats.audioVideoSyncDriftMs,
              timestamp: Date.now(),
            });
          }
        );

        // Initialize local media
        await webrtcClientRef.current.initLocalMedia();

        // Connect WebSocket
        webrtcClientRef.current.connectSocket();

        // Start WebRTC call
        await webrtcClientRef.current.startCall();

        setIsConnected(true);
      } catch (err) {
        const errorMessage =
          err instanceof AxiosError
            ? err.response?.data?.error || err.message
            : err instanceof Error
              ? err.message
              : 'Unknown error';
        setError(errorMessage);
        console.error('Session initialization error:', errorMessage);
      } finally {
        setIsConnecting(false);
      }
    },
    [signalingUrl]
  );

  // Hot-swap face identity
  const switchAsset = useCallback(
    (assetId: number) => {
      if (!webrtcClientRef.current) {
        setError('WebRTC client not initialized');
        return;
      }

      webrtcClientRef.current.switchAsset(assetId);
    },
    []
  );

  // Request GPU health status
  const getGPUHealth = useCallback(() => {
    if (!webrtcClientRef.current) {
      setError('WebRTC client not initialized');
      return;
    }

    // Dispatch command via WebSocket
    webrtcClientRef.current.switchAsset(0); // Placeholder; in production, use proper command dispatch
  }, []);

  // Update voice pitch parameter
  const updateVoicePitch = useCallback(
    (pitch: number) => {
      if (!webrtcClientRef.current) {
        setError('WebRTC client not initialized');
        return;
      }

      // Send pitch update command via WebSocket
      webrtcClientRef.current.switchAsset(0); // Placeholder; in production, use proper command dispatch
    },
    []
  );

  // Disconnect and cleanup
  const disconnect = useCallback(() => {
    if (webrtcClientRef.current) {
      webrtcClientRef.current.close();
      webrtcClientRef.current = null;
    }

    if (streamReaderRef.current) {
      streamReaderRef.current.cancel();
      streamReaderRef.current = null;
    }

    setSession(null);
    setStats(null);
    setIsConnected(false);
    setError(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    session,
    stats,
    isConnecting,
    isConnected,
    error,
    initSession,
    switchAsset,
    getGPUHealth,
    updateVoicePitch,
    disconnect,
    metrics,
  };
}

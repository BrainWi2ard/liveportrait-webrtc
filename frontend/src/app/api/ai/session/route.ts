import { streamText, generateText } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import { NextRequest, NextResponse } from 'next/server';
import crypto from 'crypto';

const openai = createOpenAI({
  apiKey: process.env.OPENAI_API_KEY || '',
});

export const runtime = 'nodejs';

interface SessionTokenPayload {
  sessionId: string;
  userId: string;
  timestamp: number;
  expiresIn: number;
}

interface AssetHotSwapCommand {
  type: 'swap_identity' | 'update_voice_pitch' | 'get_gpu_health';
  targetAssetId?: number;
  voicePitch?: number;
}

function generateSessionToken(userId: string): SessionTokenPayload {
  const sessionId = crypto.randomUUID();
  const timestamp = Date.now();
  const expiresIn = 3600; // 1 hour

  return {
    sessionId,
    userId,
    timestamp,
    expiresIn,
  };
}

function encodeToken(payload: SessionTokenPayload): string {
  return Buffer.from(JSON.stringify(payload)).toString('base64');
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { userId, command } = body as { userId: string; command?: AssetHotSwapCommand };

    if (!userId) {
      return NextResponse.json(
        { error: 'userId is required' },
        { status: 400 }
      );
    }

    // Generate streaming session token
    const sessionPayload = generateSessionToken(userId);
    const encodedToken = encodeToken(sessionPayload);

    // If there's a command, stream the response via AI SDK
    if (command) {
      const systemPrompt = `You are a real-time streaming orchestrator for LivePortrait-WebRTC.
      You handle dynamic asset hot-swapping, GPU health monitoring, and voice parameter tuning.
      Respond concisely with actionable JSON-formatted commands.`;

      const userMessage = `Process this WebRTC streaming command: ${JSON.stringify(command)}`;

      const response = await streamText({
        model: openai('gpt-4-turbo-preview'),
        system: systemPrompt,
        messages: [
          {
            role: 'user',
            content: userMessage,
          },
        ],
        temperature: 0.3,
      });

      // Stream the response back to the client
      const encoder = new TextEncoder();
      const stream = new ReadableStream({
        async start(controller) {
          // Send session token first
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: 'session_token',
                payload: sessionPayload,
                encodedToken,
              })}\n\n`
            )
          );

          // Stream AI response
          try {
            for await (const chunk of response.textStream) {
              controller.enqueue(
                encoder.encode(
                  `data: ${JSON.stringify({
                    type: 'orchestration_stream',
                    chunk,
                  })}\n\n`
                )
              );
            }
          } catch (error) {
            console.error('Streaming error:', error);
          } finally {
            controller.close();
          }
        },
      });

      return new NextResponse(stream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          Connection: 'keep-alive',
        },
      });
    }

    // Return session token without streaming
    return NextResponse.json(
      {
        sessionId: sessionPayload.sessionId,
        userId: sessionPayload.userId,
        encodedToken,
        expiresIn: sessionPayload.expiresIn,
        timestamp: sessionPayload.timestamp,
      },
      { status: 200 }
    );
  } catch (error) {
    console.error('AI session route error:', error);
    return NextResponse.json(
      { error: 'Failed to generate streaming session' },
      { status: 500 }
    );
  }
}

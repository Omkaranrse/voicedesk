import { randomUUID } from 'crypto';
import { NextResponse } from 'next/server';
import {
  AccessToken,
  type AccessTokenOptions,
  RoomConfiguration,
  type VideoGrant,
} from 'livekit-server-sdk';

type ConnectionDetails = {
  serverUrl: string;
  roomName: string;
  participantName: string;
  participantToken: string;
};

const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;
// Optional pre-shared authentication secret boundary for token generation
const TOKEN_AUTH_SECRET = process.env.LIVEKIT_TOKEN_AUTH_SECRET;

// In-memory sliding window rate limiter per client IP: max 5 token requests per 60 seconds
const RATE_LIMIT_WINDOW_MS = 60 * 1000;
const MAX_REQUESTS_PER_WINDOW = 5;
const ipRequestHistory = new Map<string, { count: number; resetAt: number }>();

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const entry = ipRequestHistory.get(ip);

  if (!entry || now > entry.resetAt) {
    ipRequestHistory.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return false;
  }

  if (entry.count >= MAX_REQUESTS_PER_WINDOW) {
    return true;
  }

  entry.count += 1;
  return false;
}

// Don't cache results
export const revalidate = 0;

export async function POST(req: Request) {
  // 1. IP Rate Limiting to prevent denial of service and room exhaustion
  const forwardedFor = req.headers.get('x-forwarded-for');
  const clientIp = forwardedFor ? forwardedFor.split(',')[0].trim() : '127.0.0.1';

  if (isRateLimited(clientIp)) {
    return new NextResponse('Too many token requests. Please try again shortly.', {
      status: 429,
      headers: {
        'Retry-After': '60',
        'Cache-Control': 'no-store',
      },
    });
  }

  // 2. Authentication Boundary:
  // If LIVEKIT_TOKEN_AUTH_SECRET is configured, enforce strict token verification.
  // If not configured, document interface requirement and log security advisory in production.
  if (TOKEN_AUTH_SECRET) {
    const authHeader = req.headers.get('authorization');
    const customHeader = req.headers.get('x-token-auth');
    const bearerToken = authHeader?.startsWith('Bearer ') ? authHeader.substring(7) : null;
    const providedSecret = bearerToken || customHeader;

    if (!providedSecret || providedSecret !== TOKEN_AUTH_SECRET) {
      return new NextResponse('Unauthorized: Invalid or missing token authentication secret.', {
        status: 401,
        headers: { 'Cache-Control': 'no-store' },
      });
    }
  } else if (process.env.NODE_ENV === 'production') {
    console.warn(
      '[Security Warning] LIVEKIT_TOKEN_AUTH_SECRET is not configured in production environment. ' +
        'Integrate your identity provider or configure an authentication secret before going live.'
    );
  }

  try {
    if (!LIVEKIT_URL) {
      throw new Error('LIVEKIT_URL is not defined in server environment');
    }
    if (!API_KEY) {
      throw new Error('LIVEKIT_API_KEY is not defined in server environment');
    }
    if (!API_SECRET) {
      throw new Error('LIVEKIT_API_SECRET is not defined in server environment');
    }

    let roomConfig: RoomConfiguration | undefined;
    try {
      const body = await req.json();
      if (body?.room_config) {
        roomConfig = RoomConfiguration.fromJson(body.room_config, { ignoreUnknownFields: true });
      }
    } catch {
      // Body may be empty in simple audio clients; proceed with default room configuration
      roomConfig = new RoomConfiguration();
    }

    // Cryptographically secure collision-resistant identifiers (UUIDv4)
    const sessionId = randomUUID();
    const participantName = 'user';
    const participantIdentity = `voice_assistant_user_${sessionId}`;
    const roomName = `voice_assistant_room_${sessionId}`;

    const participantToken = await createParticipantToken(
      { identity: participantIdentity, name: participantName },
      roomName,
      roomConfig
    );

    const data: ConnectionDetails = {
      serverUrl: LIVEKIT_URL,
      roomName,
      participantName,
      participantToken,
    };

    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'no-store',
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Internal Server Error';
    console.error('[Token Generation Error]', error);
    return new NextResponse(message, {
      status: 500,
      headers: { 'Cache-Control': 'no-store' },
    });
  }
}

function createParticipantToken(
  userInfo: AccessTokenOptions,
  roomName: string,
  roomConfig: RoomConfiguration | undefined
): Promise<string> {
  // 10-minute token TTL provides sufficient window to connect without perpetual validity
  const at = new AccessToken(API_KEY, API_SECRET, {
    ...userInfo,
    ttl: '10m',
  });

  // Explicit minimal grant: only audio/data permissions inside the isolated session room
  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canPublishData: true,
    canSubscribe: true,
  };
  at.addGrant(grant);

  if (roomConfig) {
    at.roomConfig = roomConfig;
  }

  return at.toJwt();
}

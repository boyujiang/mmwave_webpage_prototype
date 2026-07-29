'use client';

import { useEffect } from 'react';

import type { VitalsUpdate } from '@/src/lib/realtime';

interface VitalsMessage {
  type: 'vitals_snapshot' | 'vitals_update';
  data: VitalsUpdate;
}

const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000';

const isVitalsMessage = (value: unknown): value is VitalsMessage => {
  if (typeof value !== 'object' || value === null) return false;

  const message = value as Partial<VitalsMessage>;
  return (
    (message.type === 'vitals_snapshot' ||
      message.type === 'vitals_update') &&
    typeof message.data === 'object' &&
    message.data !== null &&
    typeof message.data.resident_id === 'number'
  );
};

export function useVitalsSocket(
  onVitals: (update: VitalsUpdate) => void,
  enabled: boolean,
  residentId?: string,
) {
  useEffect(() => {
    if (!enabled) return;

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let retryCount = 0;
    let disposed = false;

    const connect = () => {
      const accessToken = localStorage.getItem('access_token');
      if (!accessToken || disposed) return;

      const path = residentId
        ? `/ws/analytics/residents/${residentId}/vitals/`
        : '/ws/analytics/vitals/';

      socket = new WebSocket(
        `${WS_BASE_URL}${path}`,
        ['access-token', accessToken],
      );

      socket.onopen = () => {
        retryCount = 0;
      };

      socket.onmessage = (event) => {
        try {
          const message: unknown = JSON.parse(event.data);
          if (isVitalsMessage(message)) {
            onVitals(message.data);
          }
        } catch {
          console.error('Received an invalid vitals WebSocket message');
        }
      };

      socket.onerror = () => {
        socket?.close();
      };

      socket.onclose = () => {
        if (disposed) return;

        const delay = Math.min(1000 * 2 ** retryCount, 30000);
        retryCount += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close(1000, 'Page closed');
    };
  }, [enabled, onVitals, residentId]);
}

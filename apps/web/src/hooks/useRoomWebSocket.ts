"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { RoomEvent } from "@/lib/types";

export type RoomConnectionState = "connecting" | "connected" | "disconnected";

export function useRoomWebSocket(roomCode: string, token: string | null) {
  const [state, setState] = useState<RoomConnectionState>("disconnected");
  const [events, setEvents] = useState<RoomEvent[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!roomCode || !token) {
      setState("disconnected");
      return;
    }

    const socket = new WebSocket(api.rooms.webSocketUrl(roomCode, token));
    socketRef.current = socket;
    setState("connecting");

    socket.onopen = () => setState("connected");
    socket.onmessage = (message: MessageEvent<string>) => {
      try {
        const event = JSON.parse(message.data) as RoomEvent;
        setEvents((current) => [...current.slice(-99), event]);
      } catch {
        setEvents((current) => [
          ...current.slice(-99),
          { event: "ERROR", detail: "Received an invalid room update" },
        ]);
      }
    };
    socket.onerror = () => setState("disconnected");
    socket.onclose = () => {
      setState("disconnected");
      if (socketRef.current === socket) socketRef.current = null;
    };

    return () => {
      socketRef.current = null;
      socket.close();
    };
  }, [roomCode, token]);

  const send = useCallback((event: Record<string, unknown>) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify(event));
    return true;
  }, []);

  return { state, events, send };
}

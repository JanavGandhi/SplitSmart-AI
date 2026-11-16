"use client";

import { useEffect, useState } from "react";
import type { ReceiptProgressEvent } from "@/lib/types";

export type SSEState = "idle" | "connecting" | "connected" | "closed" | "error";

const TERMINAL_EVENTS = new Set([
  "READY_FOR_CLAIMS",
  "PIPELINE_FAILED",
  "STREAM_END",
  "TIMEOUT",
]);

export function useReceiptSSE(url: string | null) {
  const [state, setState] = useState<SSEState>("idle");
  const [events, setEvents] = useState<ReceiptProgressEvent[]>([]);

  useEffect(() => {
    if (!url) {
      setState("idle");
      setEvents([]);
      return;
    }

    const source = new EventSource(url);
    const listeners = new Set<string>([
      "SUBSCRIBED",
      "STAGE_UPDATE",
      "OCR_COMPLETE",
      "VALIDATION_OK",
      "VALIDATION_CORRECTED",
      "READY_FOR_CLAIMS",
      "PIPELINE_FAILED",
      "STREAM_END",
      "TIMEOUT",
    ]);
    setState("connecting");

    const handleEvent = (event: Event) => {
      const message = event as MessageEvent<string>;
      try {
        const data = JSON.parse(message.data) as ReceiptProgressEvent;
        const progressEvent = { ...data, event: message.type };
        setEvents((current) => [...current.slice(-49), progressEvent]);
        if (TERMINAL_EVENTS.has(message.type)) {
          source.close();
          setState("closed");
        } else {
          setState("connected");
        }
      } catch {
        setEvents((current) => [
          ...current.slice(-49),
          { event: "error", message: "Invalid progress event received" },
        ]);
      }
    };

    listeners.forEach((name) => source.addEventListener(name, handleEvent));
    source.onopen = () => setState("connected");
    source.onerror = () => {
      setState(source.readyState === EventSource.CLOSED ? "closed" : "error");
    };

    return () => {
      source.close();
      listeners.forEach((name) => source.removeEventListener(name, handleEvent));
    };
  }, [url]);

  return { state, events };
}

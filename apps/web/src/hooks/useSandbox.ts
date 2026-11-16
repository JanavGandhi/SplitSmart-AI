"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { SandboxResponse } from "@/lib/types";

export function useSandbox() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function launch(): Promise<SandboxResponse | null> {
    setLoading(true);
    setError(null);
    try {
      return await api.sandbox.init();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not launch demo");
      return null;
    } finally {
      setLoading(false);
    }
  }

  return { launch, loading, error };
}

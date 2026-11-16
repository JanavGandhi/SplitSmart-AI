"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LoaderCircle, Rocket } from "lucide-react";
import { useSandbox } from "@/hooks/useSandbox";

export default function DemoLaunchButton({ className = "" }: { className?: string }) {
  const router = useRouter();
  const { launch, loading, error } = useSandbox();
  const [localError, setLocalError] = useState<string | null>(null);

  async function startDemo() {
    setLocalError(null);
    const result = await launch();
    if (!result) return;
    try {
      sessionStorage.setItem(
        `splitsmart.demo.receipts.${result.group_id}`,
        JSON.stringify(result.receipts),
      );
    } catch {
      setLocalError("Demo started, but receipt shortcuts could not be saved in this browser.");
    }
    router.push(`/groups/${result.group_id}`);
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button type="button" onClick={startDemo} disabled={loading} className={className || "btn-primary"}>
        {loading ? <LoaderCircle size={17} className="animate-spin" /> : <Rocket size={17} />}
        {loading ? "Preparing your demo…" : "Launch instant demo"}
      </button>
      {(error || localError) && (
        <p role="alert" className="max-w-sm text-center text-xs text-rose-300">
          {error ?? localError}
        </p>
      )}
    </div>
  );
}

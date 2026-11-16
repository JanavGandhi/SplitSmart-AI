"use client";

import { FormEvent, useState } from "react";
import { Bot, LoaderCircle, MessageCircle, Send, Sparkles, X } from "lucide-react";
import { api } from "@/lib/api";

interface ChatMessage {
  role: "assistant" | "user";
  text: string;
}

export default function CopilotDrawer({ groupId }: { groupId: string }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "Ask about this group’s spending or who should settle next.",
    },
  ]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = message.trim();
    if (!text || sending) return;
    setMessages((current) => [...current, { role: "user", text }]);
    setMessage("");
    setSending(true);
    try {
      const response = await api.copilot.chat(text, groupId);
      setMessages((current) => [...current, { role: "assistant", text: response.reply }]);
    } catch (reason) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text:
            reason instanceof Error
              ? `Copilot could not respond: ${reason.message}`
              : "Copilot could not respond. Please try again later.",
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-30 flex items-center gap-2 rounded-full border border-indigo-300/20 bg-indigo-500 px-4 py-3 text-sm font-semibold text-white shadow-xl shadow-indigo-950/60 transition hover:bg-indigo-400"
      >
        <MessageCircle size={17} /> AI Copilot
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/55 backdrop-blur-sm" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setOpen(false);
        }}>
          <aside className="flex h-full w-full max-w-md flex-col border-l border-white/10 bg-[#0a0e1b] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/[0.07] p-5">
              <div className="flex items-center gap-3">
                <span className="rounded-xl bg-indigo-400/10 p-2.5 text-indigo-200"><Bot size={19} /></span>
                <div>
                  <h2 className="font-semibold">SplitSmart Copilot</h2>
                  <p className="mt-0.5 flex items-center gap-1 text-xs text-slate-500"><Sparkles size={12} /> Group-aware assistant</p>
                </div>
              </div>
              <button type="button" aria-label="Close copilot" onClick={() => setOpen(false)} className="rounded-lg p-2 text-slate-400 hover:bg-white/10"><X size={18} /></button>
            </div>
            <div className="flex-1 space-y-3 overflow-y-auto p-5" aria-live="polite">
              {messages.map((item, index) => (
                <div key={`${item.role}-${index}`} className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  item.role === "user" ? "ml-auto bg-indigo-500/20 text-indigo-50" : "border border-white/[0.07] bg-white/[0.035] text-slate-300"
                }`}>
                  {item.text}
                </div>
              ))}
              {sending && <div className="flex items-center gap-2 text-xs text-slate-500"><LoaderCircle size={14} className="animate-spin" /> Thinking…</div>}
            </div>
            <form onSubmit={submit} className="border-t border-white/[0.07] p-4">
              <label htmlFor="copilot-message" className="sr-only">Ask SplitSmart Copilot</label>
              <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] p-2 pl-3 focus-within:border-indigo-400/50">
                <input
                  id="copilot-message"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="Ask a question about this group…"
                  maxLength={500}
                  className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-600"
                />
                <button type="submit" disabled={!message.trim() || sending} aria-label="Send message" className="rounded-lg bg-indigo-500 p-2 text-white disabled:opacity-40"><Send size={15} /></button>
              </div>
              <p className="mt-2 text-[10px] leading-relaxed text-slate-500">
                Your question and this group’s names, balances, and recent receipt totals are sent to the configured Google Gemini service.
              </p>
            </form>
          </aside>
        </div>
      )}
    </>
  );
}

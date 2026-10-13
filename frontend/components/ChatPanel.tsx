"use client";

import { useState } from "react";
import { askQuestion } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "What's our current denial rate?",
  "How much revenue is at risk right now?",
  "Which payer denies us the most?",
  "How many claims are pending recovery?",
];

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(question: string) {
    if (!question.trim() || busy) return;
    setMessages((m) => [...m, { role: "user", content: question }]);
    setInput("");
    setBusy(true);
    try {
      const res = await askQuestion(question);
      setMessages((m) => [...m, { role: "assistant", content: res.answer }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${e instanceof Error ? e.message : "request failed"}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-xl border border-hairline bg-surface">
      <div className="flex-1 overflow-y-auto p-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <p className="text-sm text-ink-muted">Ask a question about revenue, denials, or claims in plain English.</p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-hairline px-3 py-1.5 text-xs text-ink-secondary hover:bg-surface-muted"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="flex flex-col gap-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-lg whitespace-pre-wrap rounded-xl px-4 py-2.5 text-sm ${
                  m.role === "user" ? "bg-brand text-white" : "bg-surface-muted text-ink"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {busy && <div className="text-sm text-ink-muted">Thinking...</div>}
        </div>
      </div>
      <form
        onSubmit={(e) => { e.preventDefault(); send(input); }}
        className="flex gap-2 border-t border-hairline p-4"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about revenue, denials, payers..."
          className="flex-1 rounded-lg border border-hairline bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-muted"
        />
        <button
          disabled={busy}
          className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand/90 disabled:opacity-60"
        >
          Send
        </button>
      </form>
    </div>
  );
}

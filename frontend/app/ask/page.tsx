import ChatPanel from "@/components/ChatPanel";

export default function AskPage() {
  return (
    <div className="mx-auto max-w-3xl px-8 py-8">
      <h1 className="text-2xl font-semibold text-ink">Ask My Data</h1>
      <p className="mt-1 text-sm text-ink-secondary">
        Natural-language answers grounded only in your revenue/claims data - never invented numbers.
      </p>
      <div className="mt-6">
        <ChatPanel />
      </div>
    </div>
  );
}

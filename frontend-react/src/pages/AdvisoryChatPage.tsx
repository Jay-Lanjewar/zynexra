import { useEffect, useRef } from "react";
import { ArrowUp, Loader2, MessageSquareText, ShieldCheck } from "lucide-react";
import type { AppMode, ChatMessage } from "../types";
import type { ApiError } from "../api";

type AdvisoryChatPageProps = {
  messages: ChatMessage[];
  inputValue: string;
  isLoading: boolean;
  error: ApiError | null;
  sessionId: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onModeChange: (mode: AppMode | "WORKSPACE") => void;
};

export function AdvisoryChatPage({
  messages,
  inputValue,
  isLoading,
  error,
  sessionId,
  onInputChange,
  onSend,
  onModeChange,
}: AdvisoryChatPageProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  }

  return (
    <main className="mx-auto flex h-screen w-full max-w-6xl flex-col px-5 py-6 sm:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-slate-950">Advisory Chat</h1>
          <p className="mt-1 text-sm text-slate-600">Ask legal-practice questions</p>
        </div>
        <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600">
          <ShieldCheck className="h-4 w-4 text-emerald-600" aria-hidden="true" />
          <span className="hidden sm:inline">Session {sessionId.slice(0, 8)}</span>
        </div>
      </header>

<section className="grid min-h-0 flex-1 gap-6 py-5">
        <div className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
            {messages.length === 0 ? (
              <div className="mx-auto flex max-w-2xl flex-col items-center justify-center py-16 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
                  <MessageSquareText className="h-6 w-6 text-slate-600" aria-hidden="true" />
                </div>
                <h2 className="mt-4 text-xl font-semibold text-slate-950">Ask a legal-practice question</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Advisory mode keeps a running conversation and sends a stable session id to the backend.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((message) => {
                  const isUser = message.role === "user";
                  return (
                    <div key={message.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                      <div
                        className={`max-w-[82%] rounded-lg px-4 py-3 text-sm leading-6 shadow-sm ${
                          isUser
                            ? "bg-slate-950 text-white"
                            : "border border-slate-200 bg-slate-50 text-slate-800"
                        }`}
                      >
                        <div className={`mb-1 text-xs font-semibold ${isUser ? "text-slate-300" : "text-slate-500"}`}>
                          {isUser ? "You" : "Zynexra"}
                        </div>
                        <div className="whitespace-pre-wrap break-words">{message.content}</div>
                      </div>
                    </div>
                  );
                })}
                {isLoading ? (
                  <div className="flex justify-start">
                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 shadow-sm">
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                        Zynexra is typing
                      </span>
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          {error ? (
            <div className="border-t border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {error.message}
            </div>
          ) : null}

          <div className="sticky bottom-0 border-t border-slate-200 bg-white p-3">
            <div className="flex items-end gap-2 rounded-lg border border-slate-300 bg-white p-2 shadow-sm focus-within:border-slate-500 focus-within:ring-2 focus-within:ring-slate-200">
              <textarea
                value={inputValue}
                onChange={(event) => onInputChange(event.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                rows={1}
                placeholder="Ask about contract terms, negotiation positions, or legal terminology."
                className="max-h-32 min-h-10 flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400 disabled:cursor-wait"
              />
              <button
                type="button"
                onClick={onSend}
                disabled={isLoading || !inputValue.trim()}
                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-slate-950 text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                title="Send message"
              >
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <ArrowUp className="h-4 w-4" aria-hidden="true" />}
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

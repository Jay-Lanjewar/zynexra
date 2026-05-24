import { useEffect, useRef } from "react";
import { ArrowUp, Loader2, MessageSquareText, ShieldCheck, RefreshCw, AlertTriangle } from "lucide-react";
import type { AppMode, ChatMessage } from "../types";
import type { ApiError } from "../api";
import { RetryButton } from "../components/RetryButton";
import { ConfidenceBadge } from "../components/ConfidenceBadge";

type AdvisoryChatPageProps = {
  messages: ChatMessage[];
  inputValue: string;
  isLoading: boolean;
  error: ApiError | null;
  sessionId: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onModeChange: (mode: AppMode | "WORKSPACE") => void;
  onRetry?: () => void;
  isRetrying?: boolean;
  retryAttempt?: number;
};

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-2" role="status" aria-label="Assistant is typing">
      <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "0ms" }}></span>
      <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "150ms" }}></span>
      <span className="h-2 w-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "300ms" }}></span>
    </div>
  );
}

export function AdvisoryChatPage({
  messages,
  inputValue,
  isLoading,
  error,
  sessionId,
  onInputChange,
  onSend,
  onModeChange,
  onRetry,
  isRetrying = false,
  retryAttempt = 0,
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
      <header className="flex flex-col gap-4 border-b border-slate-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-slate-100">Advisory Chat</h1>
          <p className="mt-1 text-sm text-slate-400">Ask legal-practice questions</p>
        </div>
        <div className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-slate-400">
          <ShieldCheck className="h-4 w-4 text-emerald-400" aria-hidden="true" />
          <span className="hidden sm:inline">Session {sessionId.slice(0, 8)}</span>
        </div>
      </header>

      <section className="grid min-h-0 flex-1 gap-6 py-5">
        <div className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur shadow-lg shadow-black/20">
          <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
            {messages.length === 0 ? (
              <div className="mx-auto flex max-w-2xl flex-col items-center justify-center py-16 text-center animate-fade-up">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-800">
                  <MessageSquareText className="h-6 w-6 text-slate-400" aria-hidden="true" />
                </div>
                <h2 className="mt-4 text-xl font-semibold text-slate-100">Ask a legal-practice question</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">
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
                        className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${
                          isUser
                            ? "bg-indigo-500/20 border border-indigo-500/30 text-slate-100"
                            : "border border-slate-700/50 bg-slate-800/40 text-slate-300"
                        }`}
                      >
                        <div className={`mb-1 flex items-center justify-between gap-2 text-xs font-semibold ${isUser ? "text-indigo-300" : "text-slate-500"}`}>
                          <span>{isUser ? "You" : "Zynexra"}</span>
                          {!isUser && message.confidence_label && (
                            <ConfidenceBadge
                              confidence={message.confidence_score}
                              label={message.confidence_label}
                              showPercentage={false}
                            />
                          )}
                        </div>
                        <div className="whitespace-pre-wrap break-words">{message.content}</div>
                      </div>
                    </div>
                  );
                })}
                {messages.some((m) => m.role === "assistant" && m.confidence_label === "LOW") && (
                  <div className="flex justify-start">
                    <div className="max-w-[82%] rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm shadow-sm">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 flex-shrink-0 text-red-400 mt-0.5" />
                        <div>
                          <p className="font-semibold text-red-300">Low Confidence Response</p>
                          <p className="mt-0.5 text-red-400/80">
                            This response may be incomplete or unreliable. Review carefully.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                {isLoading ? (
                  <div className="flex justify-start">
                    <div className="rounded-2xl border border-slate-700/50 bg-slate-800/40 px-4 py-3 text-sm text-slate-400 shadow-sm">
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
            <div className="border-t border-amber-500/20 bg-amber-500/5 px-4 py-3">
              <p className="text-sm text-amber-400 mb-2">{error.message}</p>
              {onRetry && (
                <RetryButton
                  onRetry={onRetry}
                  isRetrying={isRetrying}
                  attempt={retryAttempt}
                  maxAttempts={3}
                  label="Retry"
                  className="justify-start"
                />
              )}
            </div>
          ) : null}

          <div className="sticky bottom-0 border-t border-slate-800 bg-slate-900/80 p-3 backdrop-blur">
            <div className="flex items-end gap-2 rounded-xl border border-slate-700 bg-slate-800/50 p-2 shadow-sm focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20">
              <textarea
                value={inputValue}
                onChange={(event) => onInputChange(event.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                rows={1}
                placeholder="Ask about contract terms, negotiation positions, or legal terminology."
                className="max-h-32 min-h-10 flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm leading-6 text-slate-200 outline-none placeholder:text-slate-500 disabled:cursor-wait"
              />
              <button
                type="button"
                onClick={onSend}
                disabled={isLoading || !inputValue.trim()}
                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-500 text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
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

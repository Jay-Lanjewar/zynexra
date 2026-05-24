export function CardSkeleton() {
  return (
    <div className="bg-slate-900/60 rounded-lg border border-slate-800 p-6 animate-pulse">
      <div className="space-y-4">
        <div className="h-4 bg-slate-700 rounded w-2/3"></div>
        <div className="h-3 bg-slate-700 rounded w-full"></div>
        <div className="h-3 bg-slate-700 rounded w-5/6"></div>
        <div className="flex gap-2">
          <div className="h-6 bg-slate-700 rounded-full w-16"></div>
          <div className="h-6 bg-slate-700 rounded-full w-20"></div>
        </div>
      </div>
    </div>
  );
}

export function HistoryListSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

export function SummarySkeleton() {
  return (
    <div className="bg-gradient-to-br from-slate-900/60 to-slate-900/40 rounded-lg border border-slate-800 p-6 animate-pulse">
      <div className="space-y-4">
        <div className="h-5 bg-slate-700 rounded w-1/3"></div>
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-10 bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ChatMessageSkeleton() {
  return (
    <div className="flex gap-3 animate-pulse">
      <div className="h-8 w-8 rounded-full bg-slate-700"></div>
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-slate-700 rounded w-16"></div>
        <div className="h-3 bg-slate-700 rounded w-3/4"></div>
        <div className="h-3 bg-slate-700 rounded w-1/2"></div>
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 p-3" role="status" aria-label="Assistant is typing">
      <span className="h-2 w-2 rounded-full bg-slate-600 animate-bounce" style={{ animationDelay: "0ms" }}></span>
      <span className="h-2 w-2 rounded-full bg-slate-600 animate-bounce" style={{ animationDelay: "150ms" }}></span>
      <span className="h-2 w-2 rounded-full bg-slate-600 animate-bounce" style={{ animationDelay: "300ms" }}></span>
    </div>
  );
}

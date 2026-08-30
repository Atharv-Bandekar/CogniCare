"use client";

interface DemoBannerProps {
  elderCount: number;
}

/**
 * Persistent banner shown when logged in with the shared demo account.
 * Always visible — never dismissible.
 */
export default function DemoBanner({ elderCount }: DemoBannerProps) {
  return (
    <div className="relative bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 rounded-xl p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <svg className="h-5 w-5 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-amber-300 mb-1">
            Shared Demo Account
          </h4>
          <p className="text-xs text-slate-400 leading-relaxed">
            You&apos;re logged in with demo credentials. Elders created by other visitors
            may appear below. Create your own elder with a unique name to try the
            full flow, or delete any existing ones.
          </p>
          <p className="text-xs text-amber-400/70 leading-relaxed mt-2">
            ⏱ The backend runs on a free-tier host and may take up to 50 seconds to
            wake up on the first action. Please be patient — it will respond after
            the cold start.
          </p>

          {elderCount > 0 && (
            <div className="mt-3">
              <span className="inline-flex items-center gap-1.5 text-xs bg-slate-800/80 text-slate-300 px-2.5 py-1 rounded-full">
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
                {elderCount} elder{elderCount !== 1 ? "s" : ""} on this account
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

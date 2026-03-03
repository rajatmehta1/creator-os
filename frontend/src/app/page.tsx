"use client";

import { signIn } from "next-auth/react";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-secondary">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="text-5xl font-bold tracking-tight text-foreground">
          Creator <span className="text-primary">OS</span>
        </h1>
        <p className="mt-4 text-xl text-muted-foreground">
          One idea. Six content pieces. All in your voice.
        </p>
        <p className="mt-2 text-muted-foreground">
          AI-native operating system for YouTube content creators
        </p>

        <div className="mt-10">
          <button
            onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
            className="inline-flex items-center gap-3 rounded-lg bg-primary px-8 py-4 text-lg font-medium text-primary-foreground shadow-lg transition-all hover:bg-primary/90 hover:shadow-xl"
          >
            <svg className="h-6 w-6" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Connect with YouTube
          </button>
        </div>

        <div className="mt-16 grid grid-cols-3 gap-8 text-left">
          <div className="rounded-lg border bg-card p-6">
            <h3 className="font-semibold text-card-foreground">Trend Scout</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Discover trending topics in your niche before they peak
            </p>
          </div>
          <div className="rounded-lg border bg-card p-6">
            <h3 className="font-semibold text-card-foreground">Script Architect</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Production-ready scripts in your authentic voice
            </p>
          </div>
          <div className="rounded-lg border bg-card p-6">
            <h3 className="font-semibold text-card-foreground">6-in-1 Output</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              YouTube, blog, thread, newsletter, podcast, and shorts
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

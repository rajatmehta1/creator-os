"use client";

import { useSession, signOut } from "next-auth/react";

export default function Header() {
  const { data: session } = useSession();

  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-6">
      <div className="flex items-center gap-4">
        <input
          type="search"
          placeholder="Search content, trends, ideas..."
          className="h-9 w-80 rounded-md border bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      <div className="flex items-center gap-4">
        <AgentStatusBar />

        {session?.user && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">
              {session.user.name}
            </span>
            {session.user.image && (
              <img
                src={session.user.image}
                alt={session.user.name || "User"}
                className="h-8 w-8 rounded-full"
              />
            )}
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

function AgentStatusBar() {
  return (
    <div className="flex items-center gap-2 rounded-full bg-secondary px-3 py-1">
      <div className="h-2 w-2 rounded-full bg-green-500" />
      <span className="text-xs text-muted-foreground">Agents ready</span>
    </div>
  );
}

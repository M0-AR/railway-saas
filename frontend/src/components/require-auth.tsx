"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";

import { ApiError, api } from "@/lib/api";
import { clearSession } from "@/lib/session";
import type { Me } from "@/lib/types";

interface MeContextValue {
  me: Me;
  refresh: () => Promise<void>;
  logout: () => void;
}

const MeContext = React.createContext<MeContextValue | null>(null);

export function useMe(): MeContextValue {
  const context = React.useContext(MeContext);
  if (!context) throw new Error("useMe must be used inside RequireAuth");
  return context;
}

function FullScreenLoader({ label }: { label: string }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3">
      <Loader2 className="h-5 w-5 animate-spin text-brand" />
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const query = useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<Me>("/me"),
    retry: false,
    staleTime: 60_000,
  });

  const unauthorized = query.error instanceof ApiError && query.error.status === 401;

  React.useEffect(() => {
    if (unauthorized) {
      clearSession();
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      router.replace(`/login?next=${next}`);
    }
  }, [unauthorized, router]);

  if (query.isLoading || unauthorized || !query.data) {
    return <FullScreenLoader label={unauthorized ? "Redirecting to sign in…" : "Loading workspace…"} />;
  }

  const value: MeContextValue = {
    me: query.data,
    refresh: async () => {
      await query.refetch();
    },
    logout: () => {
      clearSession();
      router.push("/login");
    },
  };

  return <MeContext.Provider value={value}>{children}</MeContext.Provider>;
}

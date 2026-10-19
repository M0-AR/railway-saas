"use client";

import * as React from "react";

/* One-shot deep link flag (?new=1) without `useSearchParams`, so statically
   prerendered client pages stay free of Suspense requirements. The flag is
   stripped from the URL after it fires. */
export function useDeepLinkFlag(name: string, onMatch: () => void, enabled = true): void {
  const handler = React.useRef(onMatch);

  React.useEffect(() => {
    handler.current = onMatch;
  });

  React.useEffect(() => {
    if (!enabled) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get(name) !== "1") return;
    handler.current();
    params.delete(name);
    const search = params.toString();
    window.history.replaceState(
      {},
      "",
      `${window.location.pathname}${search ? `?${search}` : ""}`,
    );
  }, [name, enabled]);
}

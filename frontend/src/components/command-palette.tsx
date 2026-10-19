"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Command } from "cmdk";
import { Search } from "lucide-react";

import { cn } from "@/lib/utils";

export interface CommandPaletteItem {
  id: string;
  label: string;
  group: string;
  icon?: React.ReactNode;
  keywords?: string;
  onRun: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: CommandPaletteItem[];
}

/* Frequency gate (docs §6 rule 1): the palette is keyboard-initiated, so it
   opens and closes instantly — no open/close animation on this surface.
   cmdash/cmdk owns combobox + aria-activedescendant semantics. */
export function CommandPalette({ open, onOpenChange, items }: CommandPaletteProps) {
  const groups = React.useMemo(() => {
    const map = new Map<string, CommandPaletteItem[]>();
    for (const item of items) {
      const list = map.get(item.group);
      if (list) list.push(item);
      else map.set(item.group, [item]);
    }
    return [...map.entries()];
  }, [items]);

  const run = React.useCallback(
    (item: CommandPaletteItem) => {
      onOpenChange(false);
      item.onRun();
    },
    [onOpenChange],
  );

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50" />
        <DialogPrimitive.Content
          aria-label="Command palette"
          className="fixed left-1/2 top-[16%] z-50 w-[min(34rem,calc(100vw-1.5rem))] -translate-x-1/2 overflow-hidden rounded-lg border border-border bg-surface-2 shadow-2xl shadow-black/50 outline-none"
        >
          <DialogPrimitive.Title className="sr-only">Command palette</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">
            Search for a page or an action, then press Enter.
          </DialogPrimitive.Description>
          <Command loop label="Command palette">
            <div className="flex items-center gap-2.5 border-b border-border px-3.5">
              <Search className="h-4 w-4 shrink-0 text-faint-foreground" />
              <Command.Input
                autoFocus
                placeholder="Search pages and actions…"
                className="h-11 w-full bg-transparent text-sm text-foreground outline-none placeholder:text-faint-foreground"
              />
            </div>
            <Command.List className="max-h-80 overflow-y-auto p-1.5">
              <Command.Empty className="px-3 py-10 text-center text-sm text-muted-foreground">
                No results.
              </Command.Empty>
              {groups.map(([group, groupItems]) => (
                <Command.Group
                  key={group}
                  heading={group}
                  className={cn(
                    "pb-1",
                    "[&_[cmdk-group-heading]]:px-2.5 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:pt-2",
                    "[&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:font-medium",
                    "[&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.08em]",
                    "[&_[cmdk-group-heading]]:text-faint-foreground",
                  )}
                >
                  {groupItems.map((item) => (
                    <Command.Item
                      key={item.id}
                      value={`${item.group} ${item.label} ${item.keywords ?? ""}`}
                      onSelect={() => run(item)}
                      className={cn(
                        "flex cursor-default select-none items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] text-muted-foreground",
                        "data-[selected=true]:bg-white/[0.06] data-[selected=true]:text-foreground",
                        "[&_svg]:h-4 [&_svg]:w-4 [&_svg]:shrink-0",
                      )}
                    >
                      {item.icon}
                      <span className="truncate">{item.label}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              ))}
            </Command.List>
          </Command>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

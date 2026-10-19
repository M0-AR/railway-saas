"use client";

import { Toaster as Sonner, toast as sonnerToast } from "sonner";

/* Toast surface is Sonner (docs §8, STD-57: never hand-roll toasts).
   The public API stays `toast({ title, description, variant })` so call sites
   are unchanged. */

type ToastVariant = "default" | "success" | "error";

interface ToastInput {
  title: string;
  description?: string;
  variant?: ToastVariant;
}

export function toast(input: ToastInput): void {
  const { title, description, variant = "default" } = input;
  const options = description ? { description } : undefined;
  if (variant === "success") {
    sonnerToast.success(title, options);
  } else if (variant === "error") {
    sonnerToast.error(title, options);
  } else {
    sonnerToast(title, options);
  }
}

export function dismissToast(): void {
  sonnerToast.dismiss();
}

export function Toaster() {
  return (
    <Sonner
      position="bottom-right"
      offset={{ bottom: 32, right: 32 }}
      mobileOffset={{ bottom: 16, right: 16 }}
      gap={14}
      visibleToasts={3}
      duration={4000}
      closeButton={false}
      richColors={false}
    />
  );
}

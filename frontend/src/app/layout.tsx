import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { Providers } from "@/components/providers";
import "./globals.css";

/* Inter Variable, self-hosted at build; metric-matched fallback is generated
   automatically (docs/UI-REDESIGN-RESEARCH.md §3, STD-visual-details-10). */
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "RailFlow — Railway Operations Console",
  description:
    "Sell railway reservations, manage trains and reports with a multi-tenant operations console.",
};

export const viewport: Viewport = {
  themeColor: "#0d0e12",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${inter.variable}`}>
      <body className="min-h-screen font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

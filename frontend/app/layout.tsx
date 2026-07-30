import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MyGlowTheory — Scheduling & Triage Workspace",
  description: "AI operator workspace for high-confidence clinic scheduling.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased dark`}>
      <body className="min-h-full flex flex-col bg-brand-obsidian text-zinc-100 font-sans">
        {children}
      </body>
    </html>
  );
}

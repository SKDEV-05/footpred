import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Football Intelligence Platform",
  description: "Local football fixture and statistics explorer",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-[#0a0a0b] text-white antialiased min-h-screen`}>
        <header className="border-b border-white/10 bg-[#0f0f11] sticky top-0 z-50 backdrop-blur-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-4 sm:gap-8">
              <h1 className="text-xl font-bold tracking-tighter text-white">
                FOOTBALL<span className="text-green-500">INTEL</span>
              </h1>
              <nav className="flex items-center gap-4 sm:gap-6 text-sm font-medium text-zinc-400">
                <Link href="/" className="hover:text-white transition-colors">
                  Matches
                </Link>
                <Link href="/evaluation" className="hover:text-white transition-colors">
                  Evaluation
                </Link>
              </nav>
            </div>
            <div className="flex items-center gap-4">
              <div className="hidden sm:block text-xs font-mono text-zinc-500 bg-white/5 px-2 py-1 rounded border border-white/10">
                Local-Only Mode
              </div>
            </div>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
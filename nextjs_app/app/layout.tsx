import type { Metadata } from "next";
import packageJson from "@/package.json";
import "./globals.css";

export const metadata: Metadata = {
  title: "Strategy Bank",
  description: "Strategiebeschreibungen erfassen, extrahieren und backtesten.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" className="h-full antialiased">
      <head>
        {/* DSGVO: Schriften über Bunny Fonts (EU-Domain), nie über den Google-Fonts-CDN */}
        <link
          rel="stylesheet"
          href="https://fonts.bunny.net/css2?family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
        />
      </head>
      <body className="min-h-full bg-background font-sans text-foreground">
        {children}
        <footer className="px-6 pb-4 font-mono text-[10px] tracking-widest text-muted-foreground">
          STRATEGY BANK · v{packageJson.version}
        </footer>
      </body>
    </html>
  );
}

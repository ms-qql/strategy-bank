import type { Metadata } from "next";
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
          href="https://fonts.bunny.net/css?family=dm-sans:300,400,500,600,700"
        />
      </head>
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}

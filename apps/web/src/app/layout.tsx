import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "SplitSmart AI — Smart Receipt Splitting & Expense Tracking",
    template: "%s | SplitSmart AI",
  },
  description:
    "Split restaurant bills instantly with Vision AI receipt scanning, real-time multiplayer claim rooms, and exact paise-precision expense tracking. No login required to join.",
  keywords: [
    "receipt splitting",
    "expense tracker",
    "bill splitter",
    "splitwise alternative",
    "UPI payments",
    "group expenses",
    "AI receipt scanner",
  ],
  authors: [{ name: "SplitSmart AI" }],
  openGraph: {
    type: "website",
    title: "SplitSmart AI",
    description: "Zero-typing AI receipt splitting with real-time multiplayer claim rooms",
    siteName: "SplitSmart AI",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  themeColor: "#6366f1",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="bg-[hsl(224,71%,4%)] text-[hsl(210,40%,96%)] antialiased">
        {children}
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: {
    default: "Codice Civico — Accountability Civica",
    template: "%s | Codice Civico",
  },
  description:
    "Motore AI di accountability civica: promesse politiche, anomalie appalti, mappa giustizia, traduzione legislativa.",
  keywords: [
    "trasparenza", "politica italiana", "appalti pubblici", "anticorruzione",
    "ANAC", "Camera dei Deputati", "Senato", "giustizia", "civic tech",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="it" suppressHydrationWarning>
      <body className="flex min-h-screen flex-col font-sans antialiased">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}

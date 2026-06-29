import type { Metadata, Viewport } from "next";
import InitColorSchemeScript from "@mui/material/InitColorSchemeScript";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "UpliftIQ — Campaign Simulator",
  description: "Incremental targeting decision engine. Spend budget where it creates conversions.",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, statusBarStyle: "default", title: "UpliftIQ" },
  icons: { icon: "/icon-192.png", apple: "/icon-192.png" },
};

export const viewport: Viewport = {
  themeColor: "#e86020",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover", // iOS safe-area insets
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body style={{ margin: 0 }}>
        {/* Prevent dark-mode flash before hydration (spec §8). */}
        <InitColorSchemeScript attribute="data" />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import { AppQueryClientProvider } from "@/state/query-client-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "COMPARION Diff Viewer",
  description: "Upload documents and inspect native side-by-side differences."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AppQueryClientProvider>{children}</AppQueryClientProvider>
      </body>
    </html>
  );
}

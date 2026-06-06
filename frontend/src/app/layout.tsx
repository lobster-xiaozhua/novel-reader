import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: {
    default: "Novel Reader - 沉浸式小说阅读器",
    template: "%s | Novel Reader",
  },
  description: "沉浸式小说阅读器，发现、收藏、阅读你喜爱的小说",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}

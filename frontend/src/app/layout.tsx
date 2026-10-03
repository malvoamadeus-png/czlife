import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CZ 人生 | 我的模拟首富路",
  description: "一条预先冻结、实时写作的平行世界人生路线。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}


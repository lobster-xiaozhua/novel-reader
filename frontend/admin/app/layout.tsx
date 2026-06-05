import type { Metadata } from 'next';
import { Providers } from '@/shared/components/Providers';
import { AdminLayout } from '@/shared/components/AdminLayout';
import '@/shared/styles/globals.css';

export const metadata: Metadata = { title: 'Admin Console', description: '小说阅读器管理后台' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <AdminLayout>{children}</AdminLayout>
        </Providers>
      </body>
    </html>
  );
}
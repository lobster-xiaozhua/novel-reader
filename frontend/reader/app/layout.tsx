import type { Metadata } from 'next';
import { Providers } from '@/shared/components/Providers';
import { ReaderLayout } from '@/shared/components/ReaderLayout';
import '@/shared/styles/globals.css';

export const metadata: Metadata = { title: 'Novel Reader', description: '沉浸式小说阅读器' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <ReaderLayout>{children}</ReaderLayout>
        </Providers>
      </body>
    </html>
  );
}
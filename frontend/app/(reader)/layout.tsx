import type { Metadata } from 'next';
import { Providers } from '@/shared/components/Providers';
import { ReaderLayout } from '@/shared/components/ReaderLayout';

export const metadata: Metadata = { title: 'Novel Reader', description: '沉浸式小说阅读器' };

export default function ReaderRootLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <ReaderLayout>{children}</ReaderLayout>
    </Providers>
  );
}

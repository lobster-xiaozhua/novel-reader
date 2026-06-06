import type { Metadata } from 'next';
import { Providers } from '@/components/Providers';
import { AdminLayout } from '@/components/AdminLayout';

export const metadata: Metadata = { title: 'Admin Console', description: '小说阅读器管理后台' };

export default function AdminRootLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <AdminLayout>{children}</AdminLayout>
    </Providers>
  );
}

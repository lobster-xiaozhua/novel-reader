import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/login'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 公开路径始终可访问
  if (PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith(p + '/'))) {
    return NextResponse.next();
  }

  // Admin 路径需要认证 + 管理员权限
  if (pathname.startsWith('/admin')) {
    const token = request.cookies.get('access_token')?.value;
    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
    // 验证 token 有效性 + 管理员权限
    try {
      const verifyUrl = new URL('/api/auth/me', request.url);
      const verifyRes = await fetch(verifyUrl, {
        headers: { Cookie: `access_token=${token}` },
      });
      if (!verifyRes.ok) {
        return NextResponse.redirect(new URL('/login', request.url));
      }
      const data = await verifyRes.json();
      if (!data?.data?.is_staff) {
        return NextResponse.redirect(new URL('/', request.url));
      }
    } catch {
      return NextResponse.redirect(new URL('/login', request.url));
    }
  }

  return NextResponse.next();
}

export const config = { matcher: ['/((?!api|_next|static|favicon).*)'] };

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/login'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith(p + '/'))) {
    return NextResponse.next();
  }

  if (pathname.startsWith('/admin')) {
    const token = request.cookies.get('access_token')?.value;
    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
    try {
      const verifyUrl = new URL('/api/v2/auth/me', request.url);
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

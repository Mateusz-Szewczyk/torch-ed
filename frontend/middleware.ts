import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const url = request.nextUrl.clone();
  const languageCookie = request.cookies.get('language');

  if (!languageCookie) {
    // Wykryj język przeglądarki lub ustaw domyślny
    const detectedLanguage = request.headers.get('accept-language')?.split(',')[0].slice(0, 2) || 'en';
    url.pathname = `/${url.pathname}`;
    const response = NextResponse.next();
    response.cookies.set('language', detectedLanguage, { path: '/' });
    return response;
  }

  return NextResponse.next();
}

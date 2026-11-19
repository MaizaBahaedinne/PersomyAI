import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "persomy_session";
const PUBLIC_PATHS = ["/login"];

/**
 * Premier filtre : sans cookie de session, les routes privées redirigent vers /login.
 * La validité réelle de la session est vérifiée côté serveur par l'API (jamais ici).
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.has(SESSION_COOKIE);
  const isPublic = PUBLIC_PATHS.includes(pathname);

  if (!hasSession && !isPublic) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api/|_next/|favicon.ico|robots.txt).*)"],
};

/// <reference types="vite/client" />
import {
  HeadContent,
  Link,
  Outlet,
  Scripts,
  createRootRoute,
} from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { createServerFn } from '@tanstack/react-start'
import * as React from 'react'
import { DefaultCatchBoundary } from '~/components/ui/DefaultCatchBoundary'
import { NotFound } from '~/components/ui/NotFound'
import appCss from '../styles/app.css?url'
import { seo } from '~/lib/seo'
import { getSupabaseServerClient } from '~/lib/supabase'

const fetchUser = createServerFn({ method: 'GET' }).handler(async () => {
  try {
    const supabase = getSupabaseServerClient()
    const { data, error: _error } = await supabase.auth.getUser()

    if (!data.user?.email) {
      return null
    }

    return {
      email: data.user.email,
    }
  } catch (err) {
    console.warn('Supabase not configured, returning null user')
    return null
  }
})

export const Route = createRootRoute({
  beforeLoad: async () => {
    const user = await fetchUser()

    return {
      user,
    }
  },
  head: () => ({
    meta: [
      {
        charSet: 'utf-8',
      },
      {
        name: 'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      ...seo({
        title:
          'Benchify, LLM Market Benchmarking',
        description: `Benchify is a LLM Market Benchmarking platform`,
      }),
    ],
    links: [
      { rel: 'stylesheet', href: appCss },
      {
        rel: 'apple-touch-icon',
        sizes: '180x180',
        href: '/apple-touch-icon.png',
      },
      {
        rel: 'icon',
        type: 'image/png',
        sizes: '32x32',
        href: '/favicon-32x32.png',
      },
      {
        rel: 'icon',
        type: 'image/png',
        sizes: '16x16',
        href: '/favicon-16x16.png',
      },
      { rel: 'manifest', href: '/site.webmanifest', color: '#fffff' },
      { rel: 'icon', href: '/favicon.ico' },
    ],
  }),
  errorComponent: (props) => {
    return (
      <RootDocument>
        <DefaultCatchBoundary {...props} />
      </RootDocument>
    )
  },
  notFoundComponent: () => <NotFound />,
  component: RootComponent,
})

function RootComponent() {
  return (
    <RootDocument>
      <Outlet />
    </RootDocument>
  )
}

function RootDocument({ children }: { children: React.ReactNode }) {
  const { user } = Route.useRouteContext()

  return (
    <html>
      <head>
        <HeadContent />
      </head>
      <body className="antialiased">
        <header className="bg-white dark:bg-zinc-900 border-b-4 border-zinc-100 dark:border-zinc-800 sticky top-0 z-50">
          <div className="layout-container py-fluid-s">
            <nav className="cluster justify-between">
              <div className="cluster gap-fluid-l">
                <Link
                  to="/"
                  className="text-fluid-xl font-black text-brand tracking-tighter hover:scale-105 transition-transform"
                >
                  BENCHIFY
                </Link>
                <div className="cluster gap-fluid-m font-bold text-zinc-500">
                  <Link
                    to="/"
                    activeProps={{
                      className: 'text-brand',
                    }}
                    activeOptions={{ exact: true }}
                    className="hover:text-brand transition-colors"
                  >
                    Home
                  </Link>
                  <Link
                    to="/memories"
                    activeProps={{
                      className: 'text-brand',
                    }}
                    className="hover:text-brand transition-colors"
                  >
                    Memories
                  </Link>
                  <Link
                    to="/concepts"
                    activeProps={{
                      className: 'text-brand',
                    }}
                    className="hover:text-brand transition-colors"
                  >
                    Concepts
                  </Link>
                  <Link
                    to="/portfolios"
                    activeProps={{
                      className: 'text-brand',
                    }}
                    className="hover:text-brand transition-colors"
                  >
                    Portfolios
                  </Link>
                </div>
              </div>
              <div className="cluster gap-fluid-m ml-auto">
                {user ? (
                  <>
                    <span className="hidden sm:inline text-sm font-medium text-zinc-400">
                      {user.email}
                    </span>
                    <Link
                      to="/logout"
                      className="btn-vibrant btn-secondary text-sm"
                    >
                      Logout
                    </Link>
                  </>
                ) : (
                  <Link
                    to="/login"
                    className="btn-vibrant btn-primary text-sm"
                  >
                    Login
                  </Link>
                )}
              </div>
            </nav>
          </div>
        </header>

        <main className="layout-container py-fluid-xl">
          {children}
        </main>

        <TanStackRouterDevtools position="bottom-right" />
        <Scripts />
      </body>
    </html>
  )
}

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
import { QueryClientProviderWrapper } from '~/lib/query-client'
import appCss from '../styles/app.css?url'
import { seo } from '~/lib/seo'
import { getSupabaseServerClient } from '~/lib/supabase'
import { PostHogProvider } from '@posthog/react'

const fetchUser = createServerFn({ method: 'GET' }).handler(async () => {
  const supabase = getSupabaseServerClient()
  const { data, error: _error } = await supabase.auth.getUser()

  if (!data.user?.email) {
    return null
  }

  return {
    email: data.user.email,
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
      <QueryClientProviderWrapper>
        <Outlet />
      </QueryClientProviderWrapper>
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
      <body>
        <PostHogProvider
          apiKey={import.meta.env.VITE_PUBLIC_POSTHOG_PROJECT_TOKEN!}
          options={{
            api_host: '/ingest',
            ui_host: import.meta.env.VITE_PUBLIC_POSTHOG_HOST || 'https://us.posthog.com',
            defaults: '2025-05-24',
            capture_exceptions: true,
            debug: import.meta.env.DEV,
          }}
        >
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3 px-6 py-4 bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 sticky top-0 z-50 backdrop-blur-md bg-opacity-80 text-sm font-bold uppercase tracking-widest">
          <Link
            to="/"
            activeProps={{
              className: 'text-blue-600',
            }}
            activeOptions={{ exact: true }}
            className="hover:text-blue-500 transition-colors"
          >
            Today
          </Link>
          <Link
            to="/memories"
            activeProps={{
              className: 'text-blue-600',
            }}
            className="hover:text-blue-500 transition-colors"
          >
            Memories
          </Link>
          <Link
            to="/posts"
            activeProps={{
              className: 'text-blue-600',
            }}
            className="hover:text-blue-500 transition-colors"
          >
            Posts
          </Link>
          <Link
            to="/concepts"
            activeProps={{
              className: 'text-blue-600',
            }}
            className="hover:text-blue-500 transition-colors"
          >
            Concepts
          </Link>
          <Link
            to="/portfolios"
            activeProps={{
              className: 'text-blue-600',
            }}
            className="hover:text-blue-500 transition-colors"
          >
            Portfolios
          </Link>
          <Link
            to="/how-it-works"
            activeProps={{
              className: 'text-blue-600',
            }}
            className="hover:text-blue-500 transition-colors"
          >
            How it Works
          </Link>
          <Link
            to="/reasoning"
            activeProps={{
              className: 'text-blue-600',
            }}
            className="hover:text-blue-500 transition-colors"
          >
            Reasoning
          </Link>
<Link
            to="/cause-and-effect"
            activeProps={{
              className: "text-blue-600",
            }}
          >
            Cause & Effect
          </Link>
          <Link
            to="/audits"
            activeProps={{
              className: "text-blue-600",
            }}
          >
            Audits
          </Link>
          <div className="ml-auto flex items-center gap-4">
            {user ? (
              <>
                <span className="text-[10px] text-zinc-400 normal-case font-medium">{user.email}</span>
                <Link to="/logout" className="hover:text-rose-500 transition-colors">Logout</Link>
              </>
            ) : (
              <Link to="/login" className="hover:text-blue-500 transition-colors">Login</Link>
            )}
          </div>
        </div>
        {children}
        <TanStackRouterDevtools position="bottom-right" />
        <Scripts />
        </PostHogProvider>
      </body>
    </html>
  )
}

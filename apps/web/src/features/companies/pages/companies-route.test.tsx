import { useMatches } from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RouteComponent } from '~/routes/companies';

type RouteMatch = ReturnType<typeof useMatches>[number];

vi.mock('@tanstack/react-router', () => {
    const useMatches = vi.fn();
    // biome-ignore lint/suspicious/noExplicitAny: test mock for router Link props
    const Link = ({ children, to }: any) => <a href={to}>{children}</a>;
    const Outlet = () => <div data-testid="router-outlet" />;
    const createFileRoute = () => () => ({ useLoaderData: () => [] });
    return { Link, Outlet, useMatches, createFileRoute };
});

describe('CompaniesRoute /companies', () => {
    beforeEach(() => {
        vi.mocked(useMatches).mockReturnValue([
            { routeId: '/companies' },
        ] as unknown as RouteMatch[]);
    });

    it('renders the company directory when no child dossier route matches', () => {
        render(<RouteComponent />);
        expect(screen.getByText('Company Intelligence & Research Dossiers')).toBeInTheDocument();
        expect(screen.queryByTestId('router-outlet')).not.toBeInTheDocument();
    });

    it('renders the outlet for a child dossier route /companies/$ticker instead of the directory', () => {
        vi.mocked(useMatches).mockReturnValue([
            { routeId: '/companies' },
            { routeId: '/companies/$ticker' },
        ] as unknown as RouteMatch[]);
        render(<RouteComponent />);
        expect(screen.getByTestId('router-outlet')).toBeInTheDocument();
        expect(
            screen.queryByText('Company Intelligence & Research Dossiers'),
        ).not.toBeInTheDocument();
    });
});

import { createFileRoute } from '@tanstack/react-router';
import { Login } from '~/shared/auth';

export const Route = createFileRoute('/login')({
    component: LoginComp,
});

function LoginComp() {
    return <Login />;
}

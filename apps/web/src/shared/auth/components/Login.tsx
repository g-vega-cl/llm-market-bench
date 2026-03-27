import { useRouter } from '@tanstack/react-router'
import { useServerFn } from '@tanstack/react-start'
import { useMutation } from '@tanstack/react-query'
import { loginFn } from '~/routes/_authed'
import { signupFn } from '~/routes/signup'
import { Auth } from './Auth'

export function Login() {
  const router = useRouter()

  const loginMutation = useMutation({
    mutationFn: loginFn,
    onSuccess: async (data) => {
      if (!data?.error) {
        await router.invalidate()
        router.navigate({ to: '/' })
        return
      }
    },
  })

  const signupMutation = useMutation({
    mutationFn: useServerFn(signupFn),
  })

  return (
    <Auth
      actionText="Login"
      status={loginMutation.status}
      onSubmit={(e) => {
        const formData = new FormData(e.target as HTMLFormElement)

        loginMutation.mutate({
          email: formData.get('email') as string,
          password: formData.get('password') as string,
        } as any)
      }}
      afterSubmit={
        loginMutation.data ? (
          <>
            <div className="text-red-400">{(loginMutation.data as any).message}</div>
            {loginMutation.data.error &&
            (loginMutation.data as any).message === 'Invalid login credentials' ? (
              <div>
                <button
                  className="text-blue-500"
                  onClick={(e) => {
                    const formData = new FormData(
                      (e.target as HTMLButtonElement).form!,
                    )

                    signupMutation.mutate({
                      email: formData.get('email') as string,
                      password: formData.get('password') as string,
                    } as any)
                  }}
                  type="button"
                >
                  Sign up instead?
                </button>
              </div>
            ) : null}
          </>
        ) : null
      }
    />
  )
}

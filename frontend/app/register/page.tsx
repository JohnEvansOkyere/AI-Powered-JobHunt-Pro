import { redirect } from 'next/navigation'

interface RegisterPageProps {
  searchParams?: Promise<{
    h?: string
  }>
}

export default async function RegisterPage({ searchParams }: RegisterPageProps) {
  const params = await searchParams
  const token = params?.h
  redirect(token ? `/auth/signup?h=${encodeURIComponent(token)}` : '/auth/signup')
}

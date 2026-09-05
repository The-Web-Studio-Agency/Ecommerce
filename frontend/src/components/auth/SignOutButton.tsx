import { logout } from '@/lib/auth/actions';

export default function SignOutButton() {
  return (
    <form action={logout}>
      <button type="submit">Sign out</button>
    </form>
  );
}

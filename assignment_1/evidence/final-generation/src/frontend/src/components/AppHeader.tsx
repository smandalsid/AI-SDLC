import { useAuth } from "./AuthProvider";

export function AppHeader() {
  const { state, signOut } = useAuth();
  if (state.status !== "signedIn") return null;

  return (
    <header className="app-header">
      <p className="app-header__name">{state.user.name}</p>
      <button type="button" className="button" onClick={() => void signOut()}>
        Sign out
      </button>
    </header>
  );
}

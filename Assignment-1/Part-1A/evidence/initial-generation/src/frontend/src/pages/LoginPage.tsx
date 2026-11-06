import { useNavigate } from "react-router-dom";
import { useAuth } from "../components/AuthProvider";
import { LoginForm } from "../components/LoginForm";
import { StatusMessage } from "../components/StatusMessage";

const EXPIRY_MESSAGE = "Your session has expired. Please sign in again.";

export function LoginPage() {
  const { state, signIn } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(username: string, password: string): Promise<void> {
    await signIn(username, password);
    await navigate("/", { replace: true });
  }

  return (
    <main className="page page--narrow">
      <h1>Sign in</h1>
      {state.status === "signedOut" && state.reason === "expired" && (
        <StatusMessage variant="error" message={EXPIRY_MESSAGE} />
      )}
      <LoginForm onSubmit={handleSubmit} />
    </main>
  );
}

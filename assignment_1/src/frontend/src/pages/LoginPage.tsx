import { useNavigate } from "react-router-dom";
import { useAuth } from "../components/AuthProvider";
import { LoginForm } from "../components/LoginForm";

export function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(username: string, password: string): Promise<void> {
    await signIn(username, password);
    await navigate("/", { replace: true });
  }

  return (
    <main className="page page--narrow">
      <h1>Sign in</h1>
      <LoginForm onSubmit={handleSubmit} />
    </main>
  );
}

import { useLoginForm } from "../hooks/useLoginForm";
import { StatusMessage } from "./StatusMessage";
import { TextField } from "./TextField";

interface LoginFormProps {
  onSubmit: (username: string, password: string) => Promise<void>;
}

export function LoginForm({ onSubmit }: LoginFormProps) {
  const form = useLoginForm(onSubmit);

  return (
    <form className="login-form" method="post" noValidate onSubmit={(event) => void form.submit(event)}>
      <TextField
        id="login-username"
        name="username"
        label="Username"
        type="text"
        autoComplete="username"
        value={form.username}
        error={form.fieldErrors.username}
        onChange={form.setUsername}
      />
      <TextField
        id="login-password"
        name="password"
        label="Password"
        type="password"
        autoComplete="current-password"
        value={form.password}
        error={form.fieldErrors.password}
        onChange={form.setPassword}
      />
      {form.failure !== null && <StatusMessage variant="error" message={form.failure} />}
      <button type="submit" className="button" disabled={form.pending}>
        Sign in
      </button>
    </form>
  );
}

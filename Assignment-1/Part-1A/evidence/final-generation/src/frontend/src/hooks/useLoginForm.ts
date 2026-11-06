import { useRef, useState, type FormEvent } from "react";
import { ApiError, describeApiError } from "../api/errors";

const MAX_USERNAME_LENGTH = 50;
const MAX_PASSWORD_LENGTH = 128;

export interface FieldErrors {
  username?: string;
  password?: string;
}

function validate(username: string, password: string): FieldErrors {
  const errors: FieldErrors = {};
  if (username === "") errors.username = "Enter your username.";
  else if (username.length > MAX_USERNAME_LENGTH)
    errors.username = `The username can have at most ${MAX_USERNAME_LENGTH} characters.`;
  if (password === "") errors.password = "Enter your password.";
  else if (password.length > MAX_PASSWORD_LENGTH)
    errors.password = `The password can have at most ${MAX_PASSWORD_LENGTH} characters.`;
  return errors;
}

function describeFailure(error: unknown): string {
  if (error instanceof ApiError && error.kind === "invalid") {
    return `Check the username (1 to ${MAX_USERNAME_LENGTH} characters) and password (1 to ${MAX_PASSWORD_LENGTH} characters).`;
  }
  return describeApiError(error);
}

export function useLoginForm(onSubmit: (username: string, password: string) => Promise<void>) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [failure, setFailure] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (inFlight.current) return;
    const errors = validate(username, password);
    setFieldErrors(errors);
    setFailure(null);
    if (errors.username !== undefined || errors.password !== undefined) return;

    inFlight.current = true;
    setPending(true);
    try {
      await onSubmit(username, password);
    } catch (error) {
      setFailure(describeFailure(error));
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  }

  return { username, setUsername, password, setPassword, fieldErrors, failure, pending, submit };
}

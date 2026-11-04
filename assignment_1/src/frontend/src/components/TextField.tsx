interface TextFieldProps {
  id: string;
  name: string;
  label: string;
  type: "text" | "password";
  autoComplete: string;
  value: string;
  error: string | undefined;
  onChange: (value: string) => void;
}

export function TextField({ id, name, label, type, autoComplete, value, error, onChange }: TextFieldProps) {
  const errorId = `${id}-error`;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        name={name}
        type={type}
        autoComplete={autoComplete}
        autoCapitalize="none"
        spellCheck={false}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error !== undefined}
        aria-describedby={error !== undefined ? errorId : undefined}
      />
      {error !== undefined && (
        <p id={errorId} className="field__error">
          {error}
        </p>
      )}
    </div>
  );
}

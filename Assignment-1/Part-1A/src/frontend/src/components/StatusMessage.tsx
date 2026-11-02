export type StatusVariant = "loading" | "empty" | "error" | "success" | "conflict";

interface StatusMessageProps {
  variant: StatusVariant;
  message: string;
  onRetry?: () => void;
}

// A symbol accompanies each variant so state is never conveyed by colour alone.
const ICONS: Record<StatusVariant, string> = {
  loading: "…",
  empty: "∅",
  error: "✕",
  success: "✓",
  conflict: "!",
};

export function StatusMessage({ variant, message, onRetry }: StatusMessageProps) {
  const role = variant === "error" || variant === "conflict" ? "alert" : "status";
  return (
    <div className={`status status--${variant}`} role={role}>
      <span className="status__icon" aria-hidden="true">
        {ICONS[variant]}
      </span>
      <p className="status__text">{message}</p>
      {variant === "error" && onRetry ? (
        <button type="button" className="button" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

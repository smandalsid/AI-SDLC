import { Component, type ReactNode } from "react";
import { StatusMessage } from "./StatusMessage";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  failed: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { failed: true };
  }

  render(): ReactNode {
    if (this.state.failed) {
      return <StatusMessage variant="error" message="Something went wrong. Please reload the page." />;
    }
    return this.props.children;
  }
}

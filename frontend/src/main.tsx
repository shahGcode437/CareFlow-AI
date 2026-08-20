import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import App from "./App.tsx";
import { queryClient } from "./lib/queryClient";
import { ThemeProvider } from "./components/theme/ThemeProvider";
import "./index.css";

// Provider order:
//   ThemeProvider is outermost so a theme change re-renders everything
//   below without disturbing QueryClient's cache; QueryClientProvider
//   sits above the router so any route can call hooks.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);

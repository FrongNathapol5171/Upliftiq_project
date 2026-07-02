"use client";
import * as React from "react";
import { useColorScheme } from "@mui/material/styles";
import type { Mode } from "@/theme";

/** Resolved light/dark mode for chart color selection (SSR-safe). */
export function useResolvedMode(): Mode {
  const { mode, systemMode } = useColorScheme();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);
  if (!mounted) return "light";
  const resolved = mode === "system" ? systemMode : mode;
  return resolved === "dark" ? "dark" : "light";
}

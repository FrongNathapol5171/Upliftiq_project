"use client";
import * as React from "react";
import { useColorScheme } from "@mui/material/styles";
import { IconButton, Tooltip } from "@mui/material";
import DarkModeIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeIcon from "@mui/icons-material/LightModeOutlined";

export default function ThemeToggle() {
  const { mode, setMode } = useColorScheme();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);
  if (!mounted) return <IconButton color="inherit" />; // avoid hydration mismatch

  const dark = mode === "dark";
  return (
    <Tooltip title={dark ? "Light mode" : "Dark mode"}>
      <IconButton color="inherit" onClick={() => setMode(dark ? "light" : "dark")}>
        {dark ? <LightModeIcon /> : <DarkModeIcon />}
      </IconButton>
    </Tooltip>
  );
}

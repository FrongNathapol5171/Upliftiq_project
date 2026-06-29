"use client";
import { createTheme } from "@mui/material/styles";

// Single source of truth for the design system (spec §8). KMITL warm orange.
// CSS-variable theming so dark mode is a class toggle with no flash.
export const theme = createTheme({
  cssVariables: { colorSchemeSelector: "data" },
  colorSchemes: {
    light: {
      palette: {
        primary: {
          main: "#e86020", // slider fill, primary button, uplift line
          dark: "#b8431a",
          light: "#fce9df",
          contrastText: "#ffffff",
        },
        // Darkened brand for small text on light surfaces (NFR-7 contrast).
        text: { primary: "#1b1b1f", secondary: "#5f6368" },
        background: { default: "#ffffff", paper: "#f7f7f8" },
        divider: "#e3e3e6",
        success: { main: "#1e8e3e" },
        warning: { main: "#f29900" },
        error: { main: "#d93025" },
      },
    },
    dark: {
      palette: {
        primary: { main: "#ff7a45", dark: "#e86020", light: "#3a2417", contrastText: "#1b1b1f" },
        text: { primary: "#e6e6e9", secondary: "#a3a3ab" },
        background: { default: "#131316", paper: "#1c1c20" },
        divider: "#34343a",
        success: { main: "#37be5f" },
        warning: { main: "#fcc419" },
        error: { main: "#ff6b5e" },
      },
    },
  },
  shape: { borderRadius: 16 },
  typography: {
    fontFamily: [
      '"Google Sans"', '"Google Sans Text"', '"Roboto"', '"Inter"',
      "system-ui", '"Noto Sans Thai"', "sans-serif",
    ].join(","),
    h1: { fontWeight: 600 },
    h2: { fontWeight: 600 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  components: {
    MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { root: { borderRadius: 999 } } },
    MuiCard: { styleOverrides: { root: { borderRadius: 20 } } },
    MuiPaper: { styleOverrides: { rounded: { borderRadius: 20 } } },
    MuiSlider: { styleOverrides: { thumb: { width: 22, height: 22 } } },
    MuiChip: { styleOverrides: { root: { borderRadius: 999 } } },
    MuiTextField: { defaultProps: { variant: "outlined", size: "medium" } },
  },
});

// Chart series colours (spec §8.2). Uplift = brand, always on top.
export const series = {
  uplift: "#e86020",
  baseline: "#5f6368",
  random: "#b0b3b8",
};

// Darkened brand for small orange TEXT on light surfaces (passes AA, §8.3).
export const BRAND_TEXT = "#9c3614";

export const SEGMENT_COLORS: Record<string, string> = {
  Persuadable: "#e86020",
  "Sure Thing": "#5f6368",
  "Lost Cause": "#b0b3b8",
  "Sleeping Dog": "#d93025",
};

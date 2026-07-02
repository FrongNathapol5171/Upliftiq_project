"use client";
import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  AppBar, Box, Chip, Divider, Drawer, FormControl, IconButton, InputLabel,
  List, ListItemButton, ListItemIcon, ListItemText, MenuItem, Select, Stack,
  Toolbar, Tooltip, Typography,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import InsightsIcon from "@mui/icons-material/Insights";
import TuneIcon from "@mui/icons-material/Tune";
import LeaderboardIcon from "@mui/icons-material/Leaderboard";
import StorageIcon from "@mui/icons-material/Storage";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CloudDoneIcon from "@mui/icons-material/CloudDone";
import ThemeToggle from "./ThemeToggle";
import { useDataset } from "@/lib/dataset-context";
import { SIDEBAR_WIDTH } from "@/theme";

const NAV = [
  { href: "/", label: "Simulator", icon: <TuneIcon /> },
  { href: "/benchmark", label: "Benchmark", icon: <LeaderboardIcon /> },
  { href: "/datasets", label: "Datasets", icon: <StorageIcon /> },
];

function Logo() {
  return (
    <Stack direction="row" alignItems="center" spacing={1} sx={{ px: 2.5, py: 2.5 }}>
      <InsightsIcon color="primary" sx={{ fontSize: 28 }} />
      <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: -0.3 }}>
        Uplift
        <Box component="span" sx={{ color: "primary.main" }}>
          IQ
        </Box>
      </Typography>
    </Stack>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const { dataset, setDataset, datasets, gemini, supabase } = useDataset();

  return (
    <Stack sx={{ height: "100%" }}>
      <Logo />

      <List sx={{ px: 1.5, flexGrow: 0 }}>
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <ListItemButton
              key={item.href}
              onClick={() => {
                router.push(item.href);
                onNavigate?.();
              }}
              selected={active}
              sx={{
                borderRadius: 999,
                mb: 0.5,
                py: 1.1,
                "&.Mui-selected": {
                  bgcolor: "primary.light",
                  color: "primary.dark",
                  "& .MuiListItemIcon-root": { color: "primary.dark" },
                  "&:hover": { bgcolor: "primary.light" },
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{ fontWeight: active ? 700 : 500 }}
              />
            </ListItemButton>
          );
        })}
      </List>

      <Divider sx={{ mx: 2.5, my: 1.5 }} />

      {/* Global dataset selector — one choice drives every page. */}
      <Box sx={{ px: 2.5 }}>
        <FormControl fullWidth size="small">
          <InputLabel id="ds-label">Dataset</InputLabel>
          <Select
            labelId="ds-label"
            label="Dataset"
            value={datasets.includes(dataset) ? dataset : ""}
            onChange={(e) => setDataset(e.target.value)}
            sx={{ borderRadius: 3 }}
          >
            {(datasets.length ? datasets : [dataset]).map((d) => (
              <MenuItem key={d} value={d}>
                {d}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Box sx={{ flexGrow: 1 }} />

      <Stack spacing={1} sx={{ px: 2.5, pb: 2.5 }}>
        <Stack direction="row" spacing={1}>
          <Tooltip title={gemini ? "Gemini explainer active" : "Gemini key not set — built-in explainer"}>
            <Chip
              size="small"
              icon={<AutoAwesomeIcon />}
              label="Gemini"
              color={gemini ? "primary" : "default"}
              variant={gemini ? "filled" : "outlined"}
            />
          </Tooltip>
          <Tooltip title={supabase ? "Scores stored in Supabase" : "Supabase not set — local Parquet"}>
            <Chip
              size="small"
              icon={<CloudDoneIcon />}
              label="Supabase"
              color={supabase ? "primary" : "default"}
              variant={supabase ? "filled" : "outlined"}
            />
          </Tooltip>
        </Stack>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Typography variant="caption" color="text.secondary">
            Theme
          </Typography>
          <ThemeToggle />
        </Stack>
      </Stack>
    </Stack>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const pathname = usePathname();
  const title = NAV.find((n) => n.href === pathname)?.label ?? "UpliftIQ";

  return (
    <Box sx={{ display: "flex", minHeight: "100dvh" }}>
      {/* Desktop: permanent sidebar. */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: "none", md: "block" },
          width: SIDEBAR_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: SIDEBAR_WIDTH,
            boxSizing: "border-box",
            borderRight: 1,
            borderColor: "divider",
            bgcolor: "background.paper",
            borderRadius: 0,
          },
        }}
        open
      >
        <SidebarContent />
      </Drawer>

      {/* Mobile: hamburger + temporary drawer. */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": { width: SIDEBAR_WIDTH, borderRadius: 0 },
        }}
      >
        <SidebarContent onNavigate={() => setMobileOpen(false)} />
      </Drawer>

      <Box sx={{ flexGrow: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        {/* Mobile top bar only — desktop navigation lives in the sidebar. */}
        <AppBar
          position="sticky"
          elevation={0}
          color="default"
          sx={{
            display: { md: "none" },
            borderBottom: 1,
            borderColor: "divider",
            bgcolor: "background.default",
          }}
        >
          <Toolbar>
            <IconButton edge="start" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
              <MenuIcon />
            </IconButton>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ ml: 1 }}>
              <InsightsIcon color="primary" />
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {title}
              </Typography>
            </Stack>
          </Toolbar>
        </AppBar>

        <Box
          component="main"
          sx={{
            flexGrow: 1,
            px: { xs: 2, sm: 3, lg: 4 },
            py: 3,
            pb: "calc(24px + env(safe-area-inset-bottom))",
            maxWidth: 1240,
            width: "100%",
            mx: "auto",
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
}

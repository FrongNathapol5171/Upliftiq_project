"use client";
import * as React from "react";
import {
  AppBar, Toolbar, Typography, Container, Box, Card, CardContent, Stack, Slider,
  TextField, InputAdornment, ToggleButton, ToggleButtonGroup, Button, Grid,
  Chip, Alert, Skeleton,
} from "@mui/material";
import InsightsIcon from "@mui/icons-material/Insights";
import DownloadIcon from "@mui/icons-material/Download";
import ThemeToggle from "@/components/ThemeToggle";
import ProfitPanel from "@/components/ProfitPanel";
import SegmentBreakdown from "@/components/SegmentBreakdown";
import QiniChart from "@/components/QiniChart";
import SegmentExplainer from "@/components/SegmentExplainer";
import { api, SimulateResponse } from "@/lib/api";

function useDebounced<T>(value: T, delay = 120) {
  const [v, setV] = React.useState(value);
  React.useEffect(() => {
    const id = setTimeout(() => setV(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return v;
}

export default function SimulatorScreen() {
  const [datasets, setDatasets] = React.useState<string[]>([]);
  const [dataset, setDataset] = React.useState("hillstrom");
  const [population, setPopulation] = React.useState(19200);
  const [budgetPct, setBudgetPct] = React.useState(30);
  const [cost, setCost] = React.useState(0.1);
  const [value, setValue] = React.useState(10);
  const [sim, setSim] = React.useState<SimulateResponse | null>(null);
  const [error, setError] = React.useState("");

  const dBudgetPct = useDebounced(budgetPct);
  const dCost = useDebounced(cost);
  const dValue = useDebounced(value);

  // Discover datasets + population on load / dataset change.
  React.useEffect(() => {
    api.health()
      .then((h) => setDatasets(h.datasets.length ? h.datasets : ["hillstrom"]))
      .catch(() => setError("Cannot reach API. Is the backend running on " + api.base + "?"));
  }, []);

  // Recompute the simulation live (NFR-2).
  React.useEffect(() => {
    const budget = Math.round((dBudgetPct / 100) * population);
    api.simulate({ budget, cost: dCost, value: dValue, dataset })
      .then((s) => {
        setSim(s);
        setPopulation(s.population);
        setError("");
      })
      .catch((e) => setError(String(e)));
  }, [dBudgetPct, dCost, dValue, dataset, population]);

  const budget = Math.round((budgetPct / 100) * population);

  return (
    <>
      <AppBar position="sticky" elevation={0} color="default"
        sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "background.default" }}>
        <Toolbar>
          <InsightsIcon color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            Uplift<span style={{ color: "var(--mui-palette-primary-main)" }}>IQ</span>
          </Typography>
          <Chip size="small" label="Campaign Simulator" variant="outlined" sx={{ mr: 1 }} />
          <ThemeToggle />
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: 3, pb: "env(safe-area-inset-bottom)" }}>
        {error && <Alert severity="warning" sx={{ mb: 2 }}>{error}</Alert>}

        {/* Controls (UX-1: budget + cost/value at the top). */}
        <Card elevation={0} sx={{ border: 1, borderColor: "divider", mb: 2 }}>
          <CardContent>
            <Stack direction={{ xs: "column", md: "row" }} spacing={3} alignItems={{ md: "center" }}>
              <Box sx={{ flexGrow: 1, minWidth: 0, width: "100%" }}>
                <Stack direction="row" justifyContent="space-between">
                  <Typography variant="subtitle2" color="text.secondary">Budget (customers contacted)</Typography>
                  <Typography variant="subtitle2" color="primary.main" fontWeight={700}>
                    {budget.toLocaleString()} / {population.toLocaleString()}
                  </Typography>
                </Stack>
                <Slider
                  value={budgetPct}
                  min={0}
                  max={100}
                  onChange={(_, v) => setBudgetPct(v as number)}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(v) => `${v}%`}
                />
              </Box>
              <TextField
                label="Cost / contact" type="number" value={cost}
                onChange={(e) => setCost(Math.max(0, Number(e.target.value)))}
                InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
                sx={{ width: { xs: "100%", md: 160 } }}
              />
              <TextField
                label="Value / conversion" type="number" value={value}
                onChange={(e) => setValue(Math.max(0, Number(e.target.value)))}
                InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
                sx={{ width: { xs: "100%", md: 180 } }}
              />
            </Stack>

            <Stack direction="row" spacing={2} alignItems="center" sx={{ mt: 2 }} flexWrap="wrap" useFlexGap>
              <ToggleButtonGroup
                exclusive size="small" value={dataset}
                onChange={(_, v) => v && setDataset(v)}
              >
                {(datasets.length ? datasets : ["hillstrom"]).map((d) => (
                  <ToggleButton key={d} value={d}>{d}</ToggleButton>
                ))}
              </ToggleButtonGroup>
              <Box sx={{ flexGrow: 1 }} />
              <Button
                variant="contained" startIcon={<DownloadIcon />}
                href={`${api.base}/api/export?dataset=${dataset}`}
              >
                Export ranked targets (CSV)
              </Button>
            </Stack>
          </CardContent>
        </Card>

        {/* Results. */}
        {!sim ? (
          <Skeleton variant="rounded" height={420} />
        ) : (
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <ProfitPanel sim={sim} />
            </Grid>
            <Grid item xs={12} md={6}>
              <SegmentBreakdown total={sim.total_segments} selected={sim.selected_segments} />
            </Grid>
            <Grid item xs={12} md={6}>
              <QiniChart points={sim.qini_points} />
            </Grid>
            <Grid item xs={12}>
              <SegmentExplainer dataset={dataset} />
            </Grid>
          </Grid>
        )}

        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 3 }}>
          Cost & value are user assumptions (A-2). Incremental conversions are estimated on a
          randomized holdout via the uplift curve — baselines always shown (FR-D2).
        </Typography>
      </Container>
    </>
  );
}

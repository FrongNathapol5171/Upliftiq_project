"use client";
import * as React from "react";
import {
  Typography, Box, Card, CardContent, Stack, Slider, TextField, InputAdornment,
  Button, Grid, Alert, Skeleton,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import ProfitPanel from "@/components/ProfitPanel";
import SegmentBreakdown from "@/components/SegmentBreakdown";
import QiniChart from "@/components/QiniChart";
import SegmentExplainer from "@/components/SegmentExplainer";
import { api, SimulateResponse } from "@/lib/api";
import { useDataset } from "@/lib/dataset-context";

function useDebounced<T>(value: T, delay = 120) {
  const [v, setV] = React.useState(value);
  React.useEffect(() => {
    const id = setTimeout(() => setV(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return v;
}

export default function SimulatorScreen() {
  const { dataset, apiError } = useDataset();
  const [population, setPopulation] = React.useState(19200);
  const [budgetPct, setBudgetPct] = React.useState(30);
  const [cost, setCost] = React.useState(0.1);
  const [value, setValue] = React.useState(10);
  const [sim, setSim] = React.useState<SimulateResponse | null>(null);
  const [error, setError] = React.useState("");

  const dBudgetPct = useDebounced(budgetPct);
  const dCost = useDebounced(cost);
  const dValue = useDebounced(value);

  // Recompute the simulation live (NFR-2).
  React.useEffect(() => {
    const budget = Math.round((dBudgetPct / 100) * population);
    api
      .simulate({ budget, cost: dCost, value: dValue, dataset })
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
      <Stack direction="row" alignItems="baseline" justifyContent="space-between" sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Campaign Simulator
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Drag the budget — incremental profit updates live against the baselines.
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          href={`${api.base}/api/export?dataset=${dataset}`}
        >
          Export ranked targets (CSV)
        </Button>
      </Stack>

      {(apiError || error) && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {apiError || error}
        </Alert>
      )}

      {/* Controls (budget + cost/value at the top). */}
      <Card elevation={0} sx={{ border: 1, borderColor: "divider", mb: 2 }}>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={3} alignItems={{ md: "center" }}>
            <Box sx={{ flexGrow: 1, minWidth: 0, width: "100%" }}>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="subtitle2" color="text.secondary">
                  Budget (customers contacted)
                </Typography>
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
              label="Cost / contact"
              type="number"
              value={cost}
              onChange={(e) => setCost(Math.max(0, Number(e.target.value)))}
              InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
              sx={{ width: { xs: "100%", md: 160 } }}
            />
            <TextField
              label="Value / conversion"
              type="number"
              value={value}
              onChange={(e) => setValue(Math.max(0, Number(e.target.value)))}
              InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
              sx={{ width: { xs: "100%", md: 180 } }}
            />
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
        Cost & value are user assumptions. Incremental conversions are estimated on a randomized
        holdout via the uplift curve — baselines always shown alongside (FR-C2).
      </Typography>
    </>
  );
}

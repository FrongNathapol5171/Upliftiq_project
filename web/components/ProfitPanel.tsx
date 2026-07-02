"use client";
import * as React from "react";
import { Card, CardContent, Stack, Typography, Box, Chip } from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import { LineChart } from "@mui/x-charts/LineChart";
import { policySeries } from "@/theme";
import { useResolvedMode } from "@/lib/useResolvedMode";
import type { SimulateResponse } from "@/lib/api";

const money = (n: number) =>
  n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export default function ProfitPanel({ sim }: { sim: SimulateResponse | null }) {
  const mode = useResolvedMode();
  if (!sim) return null;
  const colors = policySeries(mode);
  const sweep = sim.profit_sweep;
  const x = sweep.map((p) => p.budget);

  return (
    <Card elevation={0} sx={{ border: 1, borderColor: "divider" }}>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
          <TrendingUpIcon color="primary" />
          <Typography variant="overline" color="text.secondary">
            Expected incremental profit (uplift targeting)
          </Typography>
        </Stack>

        {/* The money-on-screen headline. */}
        <Typography
          variant="h2"
          color="primary.main"
          sx={{ fontWeight: 700, lineHeight: 1.1, transition: "color .2s" }}
        >
          {money(sim.uplift.incremental_profit)}
        </Typography>

        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
          <Chip
            color="primary"
            variant="filled"
            label={`+${money(sim.profit_lift_vs_propensity)} vs propensity`}
          />
          <Chip variant="outlined" label={`+${money(sim.profit_lift_vs_random)} vs random`} />
          <Chip
            variant="outlined"
            label={`${sim.uplift.incremental_conversions.toFixed(0)} incremental conversions`}
          />
        </Stack>

        {/* Uplift hero line above the baselines; random is a dashed reference. */}
        <Box sx={{ mt: 2 }}>
          <LineChart
            height={300}
            xAxis={[{ data: x, label: "Budget (customers contacted)" }]}
            yAxis={[{ valueFormatter: (v: number) => `$${(v / 1000).toLocaleString()}k` }]}
            series={[
              { id: "uplift", data: sweep.map((p) => p.uplift), label: "Uplift", color: colors.uplift, showMark: false, curve: "monotoneX" },
              { id: "propensity", data: sweep.map((p) => p.propensity), label: "Propensity", color: colors.propensity, showMark: false, curve: "monotoneX" },
              { id: "random", data: sweep.map((p) => p.random), label: "Random", color: colors.random, showMark: false, curve: "monotoneX" },
            ]}
            grid={{ horizontal: true }}
            margin={{ left: 60 }}
            sx={{
              "& .MuiLineElement-series-uplift": { strokeWidth: 2.5 },
              "& .MuiLineElement-series-random": { strokeDasharray: "6 4", strokeWidth: 1.5 },
            }}
          />
        </Box>
      </CardContent>
    </Card>
  );
}

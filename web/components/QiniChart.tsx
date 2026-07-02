"use client";
import * as React from "react";
import { Card, CardContent, Typography, Box } from "@mui/material";
import { LineChart } from "@mui/x-charts/LineChart";
import { policySeries } from "@/theme";
import { useResolvedMode } from "@/lib/useResolvedMode";
import type { Point } from "@/lib/api";

export default function QiniChart({ points }: { points: Point[] }) {
  const mode = useResolvedMode();
  if (!points?.length) return null;
  const colors = policySeries(mode);
  const x = points.map((p) => p.x);
  const model = points.map((p) => p.y);
  const last = model[model.length - 1] ?? 0;
  // Random baseline = straight line to the same endpoint.
  const random = x.map((xi) => xi * last);

  return (
    <Card elevation={0} sx={{ border: 1, borderColor: "divider", height: "100%" }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Qini curve
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Cumulative incremental conversions as more of the population is targeted by uplift rank.
        </Typography>
        <Box sx={{ mt: 1 }}>
          <LineChart
            height={280}
            xAxis={[{ data: x, label: "Fraction of population targeted", min: 0, max: 1 }]}
            series={[
              { id: "model", data: model, label: "Uplift model", color: colors.uplift, showMark: false, curve: "monotoneX" },
              { id: "random", data: random, label: "Random", color: colors.random, showMark: false, curve: "linear" },
            ]}
            grid={{ horizontal: true }}
            margin={{ left: 55 }}
            sx={{
              "& .MuiLineElement-series-model": { strokeWidth: 2.5 },
              "& .MuiLineElement-series-random": { strokeDasharray: "6 4", strokeWidth: 1.5 },
            }}
          />
        </Box>
      </CardContent>
    </Card>
  );
}

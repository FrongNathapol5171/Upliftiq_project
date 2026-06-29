"use client";
import * as React from "react";
import { Card, CardContent, Stack, Typography, Chip, Box, Tooltip } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { SEGMENT_COLORS } from "@/theme";
import type { Segments } from "@/lib/api";

const ORDER = ["Persuadable", "Sure Thing", "Lost Cause", "Sleeping Dog"];
const HINTS: Record<string, string> = {
  Persuadable: "Converts only if treated — the gold segment to target.",
  "Sure Thing": "Converts regardless — targeting wastes the incentive.",
  "Lost Cause": "Almost never converts — targeting wastes the contact.",
  "Sleeping Dog": "Contact lowers conversion — never target.",
};

export default function SegmentBreakdown({
  total,
  selected,
}: {
  total: Segments;
  selected: Segments;
}) {
  const data = ORDER.map((s) => total[s] ?? 0);
  return (
    <Card elevation={0} sx={{ border: 1, borderColor: "divider", height: "100%" }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Audience segments
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
          {ORDER.map((s) => (
            <Tooltip key={s} title={HINTS[s]}>
              <Chip
                label={`${s}: ${(total[s] ?? 0).toLocaleString()}`}
                sx={{
                  bgcolor: SEGMENT_COLORS[s],
                  color: s === "Sure Thing" || s === "Lost Cause" ? "#fff" : "#fff",
                  fontWeight: 600,
                }}
              />
            </Tooltip>
          ))}
        </Stack>
        <Box>
          <BarChart
            height={260}
            xAxis={[{ data: ORDER, scaleType: "band" }]}
            series={[
              {
                data,
                label: "Customers",
                color: "#e86020",
              },
            ]}
            colors={ORDER.map((s) => SEGMENT_COLORS[s])}
            margin={{ left: 70 }}
          />
        </Box>
        <Typography variant="caption" color="text.secondary">
          Within your current budget, {(selected["Persuadable"] ?? 0).toLocaleString()} of the
          selected customers are Persuadable.
        </Typography>
      </CardContent>
    </Card>
  );
}

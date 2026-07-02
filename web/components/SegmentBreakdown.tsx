"use client";
import * as React from "react";
import { Card, CardContent, Stack, Typography, Chip, Box, Tooltip } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { segmentColors } from "@/theme";
import { useResolvedMode } from "@/lib/useResolvedMode";
import type { Segments } from "@/lib/api";

const ORDER = ["Persuadable", "Sure Thing", "Lost Cause", "Sleeping Dog"];
const HINTS: Record<string, string> = {
  Persuadable: "Converts only if treated — the gold segment to target.",
  "Sure Thing": "Converts regardless — targeting wastes the incentive.",
  "Lost Cause": "Almost never converts — targeting wastes the contact.",
  "Sleeping Dog": "Contact lowers conversion — never target.",
};

function SegmentDot({ color }: { color: string }) {
  return (
    <Box
      component="span"
      sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: color, display: "inline-block" }}
    />
  );
}

export default function SegmentBreakdown({
  total,
  selected,
}: {
  total: Segments;
  selected: Segments;
}) {
  const mode = useResolvedMode();
  const colors = segmentColors(mode);
  const data = ORDER.map((s) => total[s] ?? 0);

  return (
    <Card elevation={0} sx={{ border: 1, borderColor: "divider", height: "100%" }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Audience segments
        </Typography>
        {/* Counts as text with a colored identity dot (never white-on-series). */}
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
          {ORDER.map((s) => (
            <Tooltip key={s} title={HINTS[s]}>
              <Chip
                variant="outlined"
                icon={<SegmentDot color={colors[s]} />}
                label={`${s}: ${(total[s] ?? 0).toLocaleString()}`}
                sx={{ fontWeight: 600, "& .MuiChip-icon": { ml: 1 } }}
              />
            </Tooltip>
          ))}
        </Stack>
        <Box>
          <BarChart
            height={260}
            xAxis={[
              {
                data: ORDER,
                scaleType: "band",
                colorMap: { type: "ordinal", values: ORDER, colors: ORDER.map((s) => colors[s]) },
              },
            ]}
            series={[{ data, label: "Customers" }]}
            barLabel="value"
            slotProps={{ legend: { hidden: true } }}
            margin={{ left: 70 }}
            sx={{ "& .MuiBarLabel-root": { fontWeight: 600 } }}
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

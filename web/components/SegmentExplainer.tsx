"use client";
import * as React from "react";
import { Card, CardContent, Typography, Stack, ToggleButton, ToggleButtonGroup, Box, CircularProgress, Chip } from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import { api } from "@/lib/api";

const SEGMENTS = ["Persuadable", "Sure Thing", "Lost Cause", "Sleeping Dog"];

export default function SegmentExplainer({ dataset }: { dataset: string }) {
  const [segment, setSegment] = React.useState("Persuadable");
  const [text, setText] = React.useState("");
  const [source, setSource] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const load = React.useCallback(
    async (seg: string) => {
      setLoading(true);
      try {
        const r = await api.explain({ segment: seg, dataset });
        setText(r.text);
        setSource(r.source);
      } catch {
        setText("Explainer unavailable.");
      } finally {
        setLoading(false);
      }
    },
    [dataset]
  );

  React.useEffect(() => {
    load(segment);
  }, [segment, dataset, load]);

  return (
    <Card elevation={0} sx={{ border: 1, borderColor: "divider" }}>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
          <AutoAwesomeIcon color="primary" fontSize="small" />
          <Typography variant="h6">Segment explainer</Typography>
          {source && (
            <Chip
              size="small"
              variant="outlined"
              label={source.startsWith("gemini") ? "Gemini" : "Built-in"}
            />
          )}
        </Stack>
        <ToggleButtonGroup
          exclusive
          size="small"
          value={segment}
          onChange={(_, v) => v && setSegment(v)}
          sx={{ flexWrap: "wrap", mb: 1.5 }}
        >
          {SEGMENTS.map((s) => (
            <ToggleButton key={s} value={s}>
              {s}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        <Box sx={{ minHeight: 64 }}>
          {loading ? (
            <CircularProgress size={22} />
          ) : (
            <Typography variant="body2" color="text.secondary">
              {text}
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}

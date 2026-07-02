"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Alert, Box, Button, Card, CardContent, Chip, Grid, Skeleton, Stack, Typography,
} from "@mui/material";
import TuneIcon from "@mui/icons-material/Tune";
import LeaderboardIcon from "@mui/icons-material/Leaderboard";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import { api, MetricsResponse } from "@/lib/api";
import { useDataset } from "@/lib/dataset-context";

const BLURBS: Record<string, string> = {
  hillstrom:
    "Classic randomized e-mail experiment (MineThatData, 2008). 64k customers, 3 arms mapped to treated/control; outcome = site visit, value = spend.",
  criteo:
    "Criteo Uplift v2.1 — large-scale ad-incrementality benchmark (Diemert et al. 2018), subsampled for development.",
  synthetic:
    "Seeded synthetic experiment with known persuadable structure — used by the offline test suite.",
};

export default function DatasetsPage() {
  const router = useRouter();
  const { datasets, dataset, setDataset, apiError } = useDataset();
  const [metrics, setMetrics] = React.useState<Record<string, MetricsResponse | null>>({});

  React.useEffect(() => {
    datasets.forEach((d) => {
      api
        .metrics(d)
        .then((m) => setMetrics((prev) => ({ ...prev, [d]: m })))
        .catch(() => setMetrics((prev) => ({ ...prev, [d]: null })));
    });
  }, [datasets]);

  if (apiError) return <Alert severity="warning">{apiError}</Alert>;
  if (!datasets.length) return <Skeleton variant="rounded" height={320} />;

  return (
    <>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Datasets
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Every dataset is a real randomized experiment, normalised to one common frame and scored
          by the seeded pipeline.
        </Typography>
      </Box>

      <Grid container spacing={2}>
        {datasets.map((d) => {
          const m = metrics[d];
          const active = d === dataset;
          return (
            <Grid item xs={12} md={6} key={d}>
              <Card
                elevation={0}
                sx={{
                  border: 1,
                  borderColor: active ? "primary.main" : "divider",
                  height: "100%",
                }}
              >
                <CardContent>
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      {d}
                    </Typography>
                    {active && <Chip size="small" color="primary" label="selected" />}
                    {m?.balance.passed && (
                      <Chip
                        size="small"
                        variant="outlined"
                        color="success"
                        icon={<CheckCircleOutlineIcon />}
                        label="randomization OK"
                      />
                    )}
                  </Stack>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                    {BLURBS[d] ?? "Scored uplift dataset."}
                  </Typography>

                  {m ? (
                    <Stack direction="row" spacing={3} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
                      <Fact k="Rows" v={m.n_rows.toLocaleString()} />
                      <Fact k="Holdout" v={m.n_holdout.toLocaleString()} />
                      <Fact k="Treatment" v={`${(m.balance.treatment_ratio * 100).toFixed(0)}%`} />
                      {m.outcome_rate !== undefined && (
                        <Fact k="Outcome rate" v={`${(m.outcome_rate * 100).toFixed(1)}%`} />
                      )}
                      <Fact k="Best model" v={m.best_learner.replace("_", "-")} />
                    </Stack>
                  ) : (
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
                      No pipeline run yet — run{" "}
                      <code>python -m pipeline.run --dataset {d}</code>.
                    </Typography>
                  )}

                  <Stack direction="row" spacing={1}>
                    <Button
                      size="small"
                      variant="contained"
                      startIcon={<TuneIcon />}
                      onClick={() => {
                        setDataset(d);
                        router.push("/");
                      }}
                    >
                      Simulate
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<LeaderboardIcon />}
                      onClick={() => {
                        setDataset(d);
                        router.push("/benchmark");
                      }}
                    >
                      Benchmark
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </>
  );
}

function Fact({ k, v }: { k: string; v: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
        {k}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>
        {v}
      </Typography>
    </Box>
  );
}

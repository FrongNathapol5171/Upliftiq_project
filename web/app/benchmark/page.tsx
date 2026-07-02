"use client";
import * as React from "react";
import {
  Alert, Box, Card, CardContent, Chip, Grid, Skeleton, Stack, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Typography,
} from "@mui/material";
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { BarChart } from "@mui/x-charts/BarChart";
import { LineChart } from "@mui/x-charts/LineChart";
import { api, MetricsResponse } from "@/lib/api";
import { useDataset } from "@/lib/dataset-context";
import { policySeries } from "@/theme";
import { useResolvedMode } from "@/lib/useResolvedMode";

const LEARNER_LABELS: Record<string, string> = {
  s_learner: "S-learner",
  t_learner: "T-learner",
  x_learner: "X-learner",
  r_learner: "R-learner",
};

function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card elevation={0} sx={{ border: 1, borderColor: "divider", height: "100%" }}>
      <CardContent>
        <Typography variant="overline" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          {value}
        </Typography>
        {sub && (
          <Typography variant="caption" color="text.secondary">
            {sub}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

export default function BenchmarkPage() {
  const { dataset, apiError } = useDataset();
  const mode = useResolvedMode();
  const colors = policySeries(mode);
  const [m, setM] = React.useState<MetricsResponse | null>(null);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    setM(null);
    api
      .metrics(dataset)
      .then((r) => {
        setM(r);
        setError("");
      })
      .catch((e) => setError(String(e)));
  }, [dataset]);

  if (apiError || error) {
    return <Alert severity="warning">{apiError || error}</Alert>;
  }
  if (!m) return <Skeleton variant="rounded" height={480} />;

  const ranked = Object.entries(m.learners).sort((a, b) => b[1].qini - a[1].qini);
  const best = m.learners[m.best_learner];
  const deciles = m.deciles ?? [];
  const qini = m.qini_points ?? [];
  const qx = qini.map((p) => p.x);
  const qy = qini.map((p) => p.y);
  const qLast = qy[qy.length - 1] ?? 0;

  return (
    <>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Meta-learner benchmark
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Seeded run (seed {m.seed}) on <b>{m.dataset}</b> — evaluated on a randomized holdout with
          uplift-appropriate metrics only.
        </Typography>
      </Box>

      {/* Headline stat tiles. */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={6} md={3}>
          <StatTile
            label="Winning model"
            value={LEARNER_LABELS[m.best_learner] ?? m.best_learner}
            sub="ranked by Qini, AUUC tie-break"
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatTile label="Qini coefficient" value={best.qini.toFixed(4)} sub="primary metric" />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatTile label="AUUC" value={best.auuc.toFixed(4)} sub="area under uplift curve" />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatTile
            label="Holdout"
            value={m.n_holdout.toLocaleString()}
            sub={`of ${m.n_rows.toLocaleString()} rows`}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        {/* Model comparison table — winner highlighted. */}
        <Grid item xs={12} md={7}>
          <Card elevation={0} sx={{ border: 1, borderColor: "divider", height: "100%" }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Model comparison
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Learner</TableCell>
                      <TableCell align="right">Qini</TableCell>
                      <TableCell align="right">AUUC</TableCell>
                      <TableCell align="right">Ranks uplift?</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {ranked.map(([name, lm]) => {
                      const isBest = name === m.best_learner;
                      return (
                        <TableRow
                          key={name}
                          sx={isBest ? { bgcolor: "primary.light", "& td": { fontWeight: 700 } } : {}}
                        >
                          <TableCell>
                            <Stack direction="row" spacing={1} alignItems="center">
                              {isBest && <EmojiEventsIcon fontSize="small" color="primary" />}
                              <span>{LEARNER_LABELS[name] ?? name}</span>
                              {isBest && <Chip size="small" color="primary" label="winner" />}
                            </Stack>
                          </TableCell>
                          <TableCell align="right">{lm.qini.toFixed(4)}</TableCell>
                          <TableCell align="right">{lm.auuc.toFixed(4)}</TableCell>
                          <TableCell align="right">
                            {lm.ranks_correctly ? (
                              <CheckCircleOutlineIcon fontSize="small" color="success" />
                            ) : (
                              <ErrorOutlineIcon fontSize="small" color="warning" />
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>

              {/* Embedded metric-discipline explainer (required in-app, FR-D1). */}
              <Alert severity="info" icon={<InfoOutlinedIcon />} sx={{ mt: 2 }}>
                <b>Why not accuracy/AUC?</b> {m.why_not_accuracy}
              </Alert>
            </CardContent>
          </Card>
        </Grid>

        {/* Experiment diagnostics. */}
        <Grid item xs={12} md={5}>
          <Card elevation={0} sx={{ border: 1, borderColor: "divider", height: "100%" }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Experiment diagnostics
              </Typography>
              <Stack spacing={1.2}>
                <Row k="Randomization balance" v={
                  m.balance.passed
                    ? <Chip size="small" color="success" label="passed" />
                    : <Chip size="small" color="warning" label="check" />
                } />
                <Row k="Treatment ratio" v={m.balance.treatment_ratio.toFixed(3)} />
                <Row k="Max |SMD|" v={m.balance.max_abs_smd.toFixed(3)} />
                <Row k="Flagged features" v={`${m.balance.n_flagged} of ${m.balance.n_features}`} />
                {m.outcome_rate !== undefined && (
                  <Row k="Base outcome rate" v={`${(m.outcome_rate * 100).toFixed(1)}%`} />
                )}
                <Row k="Pipeline runtime" v={`${m.elapsed_sec}s`} />
                <Row
                  k="Headline @ demo budget"
                  v={`+$${m.decision_demo.profit_lift_vs_propensity.toFixed(0)} vs propensity`}
                />
              </Stack>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
                Balance = standardized mean differences between treatment and control before
                modeling. Near-zero SMDs confirm the randomized experiment (FR-A3).
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Winner's uplift-by-decile. */}
        <Grid item xs={12} md={6}>
          <Card elevation={0} sx={{ border: 1, borderColor: "divider", height: "100%" }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Uplift by decile — {LEARNER_LABELS[m.best_learner] ?? m.best_learner}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Actual incremental response per predicted-uplift decile. Top deciles beating the
                bottom = the model ranks uplift correctly.
              </Typography>
              <BarChart
                height={280}
                xAxis={[{ data: deciles.map((d) => d.percentile), scaleType: "band", label: "Decile (best → worst predicted)" }]}
                series={[{ data: deciles.map((d) => d.uplift), label: "Actual uplift", color: colors.uplift }]}
                slotProps={{ legend: { hidden: true } }}
                grid={{ horizontal: true }}
                margin={{ left: 55 }}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Winner's Qini curve. */}
        <Grid item xs={12} md={6}>
          <Card elevation={0} sx={{ border: 1, borderColor: "divider", height: "100%" }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Qini curve — {LEARNER_LABELS[m.best_learner] ?? m.best_learner}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Cumulative incremental outcomes vs fraction targeted; dashed line = random.
              </Typography>
              <LineChart
                height={280}
                xAxis={[{ data: qx, label: "Fraction targeted", min: 0, max: 1 }]}
                series={[
                  { id: "model", data: qy, label: "Uplift model", color: colors.uplift, showMark: false, curve: "monotoneX" },
                  { id: "random", data: qx.map((x) => x * qLast), label: "Random", color: colors.random, showMark: false },
                ]}
                grid={{ horizontal: true }}
                margin={{ left: 55 }}
                sx={{
                  "& .MuiLineElement-series-model": { strokeWidth: 2.5 },
                  "& .MuiLineElement-series-random": { strokeDasharray: "6 4", strokeWidth: 1.5 },
                }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <Stack direction="row" justifyContent="space-between" alignItems="center">
      <Typography variant="body2" color="text.secondary">
        {k}
      </Typography>
      <Typography variant="body2" component="div" sx={{ fontWeight: 600 }}>
        {v}
      </Typography>
    </Stack>
  );
}

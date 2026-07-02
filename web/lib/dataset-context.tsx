"use client";
import * as React from "react";
import { api } from "./api";

interface DatasetCtx {
  dataset: string;
  setDataset: (d: string) => void;
  datasets: string[];
  gemini: boolean;
  supabase: boolean;
  apiError: string;
}

const Ctx = React.createContext<DatasetCtx>({
  dataset: "hillstrom",
  setDataset: () => {},
  datasets: [],
  gemini: false,
  supabase: false,
  apiError: "",
});

export function DatasetProvider({ children }: { children: React.ReactNode }) {
  const [dataset, setDatasetState] = React.useState("hillstrom");
  const [datasets, setDatasets] = React.useState<string[]>([]);
  const [gemini, setGemini] = React.useState(false);
  const [supabase, setSupabase] = React.useState(false);
  const [apiError, setApiError] = React.useState("");

  React.useEffect(() => {
    const saved = window.localStorage.getItem("upliftiq.dataset");
    if (saved) setDatasetState(saved);
    api
      .health()
      .then((h) => {
        setDatasets(h.datasets);
        setGemini(h.gemini);
        setSupabase(h.supabase);
        if (h.datasets.length && saved && !h.datasets.includes(saved)) {
          setDatasetState(h.datasets[0]);
        }
      })
      .catch(() => setApiError(`Cannot reach the API at ${api.base}. Is the backend running?`));
  }, []);

  const setDataset = React.useCallback((d: string) => {
    setDatasetState(d);
    window.localStorage.setItem("upliftiq.dataset", d);
  }, []);

  return (
    <Ctx.Provider value={{ dataset, setDataset, datasets, gemini, supabase, apiError }}>
      {children}
    </Ctx.Provider>
  );
}

export const useDataset = () => React.useContext(Ctx);

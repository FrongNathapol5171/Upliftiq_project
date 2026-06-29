-- UpliftIQ — Supabase score store schema
-- Run once in the Supabase SQL editor (Project → SQL).
-- The pipeline upserts per-customer uplift scores here; the API reads them.

create table if not exists public.uplift_scores (
    dataset    text    not null,
    id         bigint  not null,
    uplift     double precision,
    base_rate  double precision,
    segment    text,
    "T"        smallint,         -- treatment flag (0/1)
    "Y"        smallint,         -- observed outcome (0/1)
    value      double precision, -- outcome value (e.g. spend)
    primary key (dataset, id)
);

create index if not exists uplift_scores_dataset_idx
    on public.uplift_scores (dataset);

create index if not exists uplift_scores_uplift_idx
    on public.uplift_scores (dataset, uplift desc);

-- Benchmark metrics per model × dataset (for the dashboard / /api/metrics).
create table if not exists public.uplift_metrics (
    dataset   text not null,
    learner   text not null,
    qini      double precision,
    auuc      double precision,
    is_best   boolean default false,
    created_at timestamptz default now(),
    primary key (dataset, learner)
);

-- Row Level Security: enable, and allow the service role full access.
-- (The pipeline uses the service-role key; the browser never touches this.)
alter table public.uplift_scores  enable row level security;
alter table public.uplift_metrics enable row level security;

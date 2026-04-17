-- PHANTOM Database Schema
-- Optimized for time-series data storage of OHLCV candles and trading setups.

-- Table: candles
-- Stores historical and intraday candle data for multiple instruments and timeframes.
CREATE TABLE candles (
  id           bigserial PRIMARY KEY,
  security_id  integer NOT NULL,
  symbol       text,
  exchange     text,
  tf           text NOT NULL,
  open         numeric(12,2),
  high         numeric(12,2),
  low          numeric(12,2),
  close        numeric(12,2),
  volume       bigint,
  timestamp    timestamptz NOT NULL
);

CREATE TABLE phantom_setups (
  id            bigserial PRIMARY KEY,
  security_id   integer NOT NULL,
  symbol        text,
  mode          text,
  bias_tf       text,
  pattern_tf    text,
  entry_tf      text,
  sweep_price   numeric(12,2),
  fvg_top       numeric(12,2),
  fvg_bottom    numeric(12,2),
  entry_price   numeric(12,2),
  sl            numeric(12,2),
  tp1           numeric(12,2),
  tp2           numeric(12,2),
  tp3           numeric(12,2),
  rr            numeric(5,2),
  state         text,
  outcome       text,
  created_at    timestamptz DEFAULT now()
);

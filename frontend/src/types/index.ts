// TypeScript types mirroring the backend Pydantic models (app/models/state.py).

export interface Holding {
  ticker: string;
  qty: number;
  avg_entry_price: number;
  current_price: number;
  market_value: number;
}

export interface BriefSection {
  title: string;
  body: string;
  tickers: string[];
}

export interface Alert {
  ticker: string;
  type: string;
  title: string;
  body: string;
  triggered_at: string;
  read: boolean;
}

export interface Brief {
  user_id: string;
  date: string;
  headline: string;
  portfolio_health: number;
  sections: BriefSection[];
  alerts: Alert[];
}

export interface PortfolioSummary {
  total_market_value: number;
  num_holdings: number;
  tickers: string[];
}

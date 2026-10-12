from dataclasses import asdict, dataclass
import json
import pandas as pd


@dataclass(frozen=True)
class Protocol:
    study_start: str = "2021-10-01"
    study_end: str = "2025-12-31"
    evaluation_start: str = "2023-01-01"
    holdout_start: str = "2025-01-01"
    lookback: int = 63
    horizon: int = 20
    loss_threshold: float = 0.10
    downside_target_daily: float = 0.0
    screening_profile: str = "research_30"
    financial_max_age_days: int = 400
    minimum_training_dates: int = 126
    minimum_training_rows: int = 300
    calibration_dates: int = 40
    refit_sessions: int = 20
    trees: int = 128
    max_depth: int = 6
    min_samples_leaf: int = 12
    random_state: int = 42
    rebalance_sessions: int = 5
    max_stock_weight: float = 0.10
    base_weight: str = "equal"
    exposure_policy: str = "mean_score"
    commission_bps: float = 5.0
    slippage_bps: float = 10.0
    initial_capital: float = 100000.0
    annual_sessions: int = 252
    cash_return_daily: float = 0.0

    def __post_init__(self):
        dates = [pd.Timestamp(x) for x in (
            self.study_start, self.evaluation_start, self.holdout_start, self.study_end
        )]
        if not dates[0] < dates[1] <= dates[2] <= dates[3]:
            raise ValueError("Require study_start < evaluation_start <= holdout_start <= study_end")
        if self.screening_profile not in {"research_30", "attested_membership"}:
            raise ValueError("Unknown screening profile")
        if self.base_weight not in {"equal", "market_cap"}:
            raise ValueError("Unknown base weight")
        if self.exposure_policy not in {"mean_score", "fully_invested"}:
            raise ValueError("Unknown exposure policy")
        for field in ("lookback", "horizon", "minimum_training_dates", "minimum_training_rows",
                      "calibration_dates", "refit_sessions", "trees", "max_depth",
                      "min_samples_leaf", "rebalance_sessions", "annual_sessions",
                      "financial_max_age_days"):
            if getattr(self, field) < 2:
                raise ValueError(f"{field} must be >= 2")
        if self.lookback < 10 or self.minimum_training_dates <= self.horizon:
            raise ValueError("Insufficient feature/training history")
        if not 0 < self.loss_threshold < 1 or not 0 < self.max_stock_weight <= 1:
            raise ValueError("Invalid loss threshold or position cap")
        if not 0 <= self.commission_bps <= 100 or not 0 <= self.slippage_bps <= 100:
            raise ValueError("Costs must be between 0 and 100 bps per traded notional")
        if self.initial_capital <= 0 or self.cash_return_daily <= -1:
            raise ValueError("Invalid capital or cash return")

    @classmethod
    def from_json(cls, text):
        return cls(**json.loads(text))

    def to_dict(self):
        return asdict(self)

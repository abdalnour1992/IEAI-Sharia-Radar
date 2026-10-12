"""Date-grouped, purged walk-forward learning with a frozen final holdout."""
from dataclasses import dataclass
from hashlib import sha256
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from .features import FEATURES


class TrainingUnavailable(ValueError):
    pass


def logit(values):
    p = np.clip(values, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p)).reshape(-1, 1)


@dataclass
class RiskModel:
    forest: object
    calibrator: object
    audit: dict

    def predict(self, features):
        raw = self.forest.predict_proba(features[FEATURES])[:, 1]
        return self.calibrator.predict_proba(logit(raw))[:, 1]


def fit_at(panel, decision_date, protocol):
    date = pd.Timestamp(decision_date)
    finite = np.isfinite(panel[FEATURES]).all(axis=1)
    history = panel[finite & panel.eligible & panel.target_event.notna()
                    & (panel.date >= pd.Timestamp(protocol.study_start))
                    & (panel.date < date) & (panel.label_end < date)].copy()
    history = history.sort_values(["date", "symbol"])
    dates = sorted(history.date.unique())
    if len(dates) < protocol.minimum_training_dates + protocol.calibration_dates + protocol.horizon:
        raise TrainingUnavailable("Insufficient matured, date-grouped history")
    calibration_start = pd.Timestamp(dates[-protocol.calibration_dates])
    # Labels in training must mature before the calibration decision window starts.
    training = history[history.label_end < calibration_start]
    calibration = history[history.date >= calibration_start]
    if len(training) < protocol.minimum_training_rows or training.date.nunique() < protocol.minimum_training_dates:
        raise TrainingUnavailable("Insufficient training rows after purging")
    if training.target_event.nunique() != 2 or calibration.target_event.nunique() != 2:
        raise TrainingUnavailable("Both event classes are required in training and calibration")
    forest = RandomForestClassifier(
        n_estimators=protocol.trees, max_depth=protocol.max_depth,
        min_samples_leaf=protocol.min_samples_leaf, random_state=protocol.random_state,
        n_jobs=1,
    )
    forest.fit(training[FEATURES], training.target_event.astype(int))
    raw = forest.predict_proba(calibration[FEATURES])[:, 1]
    calibrator = LogisticRegression(random_state=protocol.random_state, C=1.0)
    calibrator.fit(logit(raw), calibration.target_event.astype(int))
    fingerprint = sha256((training[["date", "symbol", *FEATURES, "target_event"]].to_csv(index=False)
                          + calibration[["date", "symbol", *FEATURES, "target_event"]].to_csv(index=False)
                          + json.dumps(protocol.to_dict(), sort_keys=True)).encode()).hexdigest()
    audit = {
        "decision_date": date.isoformat(), "model_id": fingerprint,
        "training_rows": len(training), "calibration_rows": len(calibration),
        "training_feature_end": training.date.max().isoformat(),
        "training_label_end": training.label_end.max().isoformat(),
        "calibration_start": calibration_start.isoformat(),
        "calibration_label_end": calibration.label_end.max().isoformat(),
        "status": "trained_and_calibrated",
    }
    return RiskModel(forest, calibrator, audit)


def walk_forward(panel, protocol):
    dates = sorted(panel.loc[(panel.date >= pd.Timestamp(protocol.evaluation_start))
                             & (panel.date <= pd.Timestamp(protocol.study_end)), "date"].unique())
    model, audit, scores = None, [], []
    last_fit_index = -protocol.refit_sessions
    holdout = pd.Timestamp(protocol.holdout_start)
    for i, value in enumerate(dates):
        date = pd.Timestamp(value)
        if date < holdout and (model is None or i - last_fit_index >= protocol.refit_sessions):
            try:
                model = fit_at(panel, date, protocol)
                last_fit_index = i
                audit.append(model.audit.copy())
            except TrainingUnavailable as exc:
                audit.append({"decision_date": date.isoformat(), "status": "training_unavailable", "reason": str(exc)})
        rows = panel[panel.date == date].copy()
        rows["event_probability"] = np.nan
        rows["score"] = np.nan
        rows["model_id"] = ""
        rows["holdout"] = date >= holdout
        if model is not None:
            valid = rows.eligible & np.isfinite(rows[FEATURES]).all(axis=1)
            if valid.any():
                probability = model.predict(rows.loc[valid])
                rows.loc[valid, "event_probability"] = probability
                rows.loc[valid, "score"] = 100 * (1 - probability)
                rows.loc[valid, "model_id"] = model.audit["model_id"]
        scores.append(rows)
    if not scores:
        raise TrainingUnavailable("No evaluation sessions in the dataset")
    result = pd.concat(scores, ignore_index=True)
    if not result.score.notna().any():
        raise TrainingUnavailable("No valid model. Supply sufficient historical observations and both loss-event classes")
    return result, pd.DataFrame(audit)


def forecast_metrics(scores):
    outcomes = []
    for name, rows in scores.groupby("holdout"):
        valid = rows.event_probability.notna() & rows.target_event.notna()
        evaluated = rows[valid]
        record = {"sample": "frozen_holdout" if name else "walk_forward",
                  "observations": len(evaluated), "events": int(evaluated.target_event.sum()),
                  "scored_observations": int(rows.event_probability.notna().sum())}
        if len(evaluated):
            y, p = evaluated.target_event.astype(int), evaluated.event_probability
            record.update(brier_score=float(brier_score_loss(y, p)),
                          log_loss=float(log_loss(y, p, labels=[0, 1])),
                          prevalence=float(y.mean()),
                          roc_auc=float(roc_auc_score(y, p)) if y.nunique() == 2 else None)
        outcomes.append(record)
    return outcomes

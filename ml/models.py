"""
Machine Learning Classifiers & Pipelines for SolRPDS Rug Pull Detection.
Includes:
1. Calibrated Logistic Regression (StandardScaler + L2 regularization)
2. Random Forest Classifier
3. LightGBM / Gradient Boosting Classifier
Strictly guarantees that Scaler & Imputer are fit ONLY on TRAIN.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from lightgbm import LGBMClassifier
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False


@dataclass
class EvaluationMetrics:
    pr_auc: float
    roc_auc: float
    precision: float
    recall: float
    fnr: float  # False Negative Rate (Missed Rug Rate)
    f1: float
    brier_score: float
    confusion_mat: List[List[int]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pr_auc": round(self.pr_auc, 4),
            "roc_auc": round(self.roc_auc, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "fnr": round(self.fnr, 4),
            "f1": round(self.f1, 4),
            "brier_score": round(self.brier_score, 4),
            "confusion_matrix": self.confusion_mat,
        }


class RugClassifierPipeline:
    def __init__(self, model_type: str = "calibrated_logistic"):
        self.model_type = model_type
        self.imputer = SimpleImputer(strategy="median")
        self.scaler = StandardScaler()
        self.model: Any = None
        self.is_fitted = False

        if model_type == "calibrated_logistic":
            base_lr = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
            self.model = CalibratedClassifierCV(estimator=base_lr, method="sigmoid", cv=3)
        elif model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=8,
                min_samples_split=10,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
        elif model_type == "lightgbm":
            if HAS_LIGHTGBM:
                self.model = LGBMClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.05,
                    class_weight="balanced",
                    random_state=42,
                    verbose=-1,
                )
            else:
                self.model = GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.05,
                    random_state=42,
                )
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

    def fit(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        """
        Fits imputer, scaler, and classifier strictly on the TRAIN set only.
        """
        # Step 1: Fit and transform imputer on train
        X_imp = self.imputer.fit_transform(X_train)

        # Step 2: Fit and transform scaler on train
        X_scaled = self.scaler.fit_transform(X_imp)

        # Step 3: Fit model on train
        self.model.fit(X_scaled, y_train)
        self.is_fitted = True

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predicting probabilities.")
        X_imp = self.imputer.transform(X)
        X_scaled = self.scaler.transform(X_imp)
        return self.model.predict_proba(X_scaled)[:, 1]

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        probas = self.predict_proba(X)
        return (probas >= threshold).astype(int)

    def evaluate(self, X_eval: np.ndarray, y_eval: np.ndarray, threshold: float = 0.5) -> EvaluationMetrics:
        probas = self.predict_proba(X_eval)
        preds = (probas >= threshold).astype(int)

        pr_auc = float(average_precision_score(y_eval, probas))
        roc_auc = float(roc_auc_score(y_eval, probas))
        prec = float(precision_score(y_eval, preds, zero_division=0))
        rec = float(recall_score(y_eval, preds, zero_division=0))
        f1 = float(f1_score(y_eval, preds, zero_division=0))
        brier = float(brier_score_loss(y_eval, probas))

        cm = confusion_matrix(y_eval, preds)
        # Confusion matrix: [[TN, FP], [FN, TP]]
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
            fnr = float(fn / (tp + fn)) if (tp + fn) > 0 else 0.0
            cm_list = [[int(tn), int(fp)], [int(fn), int(tp)]]
        else:
            fnr = 0.0
            cm_list = cm.tolist()

        return EvaluationMetrics(
            pr_auc=pr_auc,
            roc_auc=roc_auc,
            precision=prec,
            recall=rec,
            fnr=fnr,
            f1=f1,
            brier_score=brier,
            confusion_mat=cm_list,
        )

    def save(self, filepath: str) -> None:
        with open(filepath, "wb") as fp:
            pickle.dump(self, fp)

    @classmethod
    def load(cls, filepath: str) -> RugClassifierPipeline:
        with open(filepath, "rb") as fp:
            return pickle.load(fp)

"""
utils/ai_predictor.py
----------------------
A small, self-contained AI feature: "Placement Readiness Score".

Rather than depending on an external dataset, we bootstrap a synthetic but
realistic training set that encodes intuitive domain knowledge (higher
attendance + higher CGPA + fewer backlogs => more likely to be placement
ready), then fit a scikit-learn Logistic Regression model on it. This is a
lightweight, explainable model (not a black box) so its coefficients can
be shown to students as feedback -- appropriate for a college project.

The model trains once at process start (a few milliseconds) and is reused
for every prediction request.
"""
import random
import numpy as np
from sklearn.linear_model import LogisticRegression

_model = None
_feature_names = ["attendance_pct", "cgpa", "backlogs"]


def _generate_synthetic_training_data(n=1200, seed=7):
    rng = random.Random(seed)
    X, y = [], []
    for _ in range(n):
        attendance = rng.uniform(40, 100)
        cgpa = rng.uniform(4.0, 10.0)
        backlogs = rng.choice([0, 0, 0, 1, 1, 2, 3])
        # latent "readiness score" -- domain-informed weighting
        score = (attendance / 100) * 0.35 + (cgpa / 10) * 0.55 - backlogs * 0.12
        score += rng.uniform(-0.08, 0.08)  # noise
        label = 1 if score >= 0.55 else 0
        X.append([attendance, cgpa, backlogs])
        y.append(label)
    return np.array(X), np.array(y)


def _get_model():
    global _model
    if _model is None:
        X, y = _generate_synthetic_training_data()
        _model = LogisticRegression()
        _model.fit(X, y)
    return _model


def predict_placement_readiness(attendance_pct, cgpa, backlogs):
    """
    Returns dict: { probability (0-100), label, top_factor }
    """
    model = _get_model()
    x = np.array([[attendance_pct, cgpa, backlogs]])
    proba = float(model.predict_proba(x)[0][1])
    pct = round(proba * 100, 1)

    if pct >= 70:
        label = "Placement Ready"
    elif pct >= 45:
        label = "Needs Improvement"
    else:
        label = "At Risk"

    # Simple explainability: which factor is dragging the score down most,
    # relative to a "healthy" reference student (90% attendance, 8.5 cgpa, 0 backlogs)
    ref = {"attendance_pct": 90, "cgpa": 8.5, "backlogs": 0}
    coefs = dict(zip(_feature_names, model.coef_[0]))
    gaps = {
        "attendance_pct": (ref["attendance_pct"] - attendance_pct) / 100 * coefs["attendance_pct"],
        "cgpa": (ref["cgpa"] - cgpa) / 10 * coefs["cgpa"],
        "backlogs": (backlogs - ref["backlogs"]) * coefs["backlogs"] * -1,
    }
    top_factor = max(gaps, key=lambda k: gaps[k]) if pct < 70 else None
    factor_labels = {
        "attendance_pct": "Attendance",
        "cgpa": "Academic performance (CGPA)",
        "backlogs": "Pending backlogs",
    }

    return {
        "probability": pct,
        "label": label,
        "top_factor": factor_labels.get(top_factor),
    }

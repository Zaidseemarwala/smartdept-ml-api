import joblib
import os

MODEL_PATH = "saved_models/model.pkl"

_model = None


def load_model():
    global _model

    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError("Model file not found. Train model first.")

        _model = joblib.load(MODEL_PATH)

    return _model


def predict(attendance, sessions):

    # validation
    if not isinstance(attendance,(int,float)):
        raise ValueError("Attendance must be number")

    if not isinstance(sessions,(int,float)):
        raise ValueError("Sessions must be number")

    # derived features (must match training)
    absences = sessions - (attendance/100)*sessions
    consistency = (attendance/100)

    features = [[
        attendance,
        sessions,
        absences,
        consistency
    ]]

    model = load_model()

    pred = model.predict(features)[0]
    prob = model.predict_proba(features)[0][1]

    return {
        "risk": "HIGH RISK" if pred==1 else "SAFE",
        "confidence": round(prob*100,2)
    }
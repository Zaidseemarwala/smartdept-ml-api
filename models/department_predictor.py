import numpy as np

def predict_department_future(att_series, submission_rate, rating, syllabus):

    if len(att_series) < 2:
        return {
            "next_attendance": 0,
            "health_score": 0,
            "confidence": 0,
            "trend_slope": 0
        }

    x = np.arange(len(att_series))
    y = np.array(att_series)

    slope, intercept = np.polyfit(x, y, 1)

    next_month = slope*(len(att_series)+4) + intercept

    health_score = (
        0.4*np.mean(att_series) +
        0.2*submission_rate +
        0.2*rating +
        0.2*syllabus
    )

    confidence = abs(slope)

    return {
        "next_attendance": round(float(next_month),3),
        "health_score": round(float(health_score),3),
        "confidence": round(float(confidence),3),
        "trend_slope": round(float(slope),4)
    }
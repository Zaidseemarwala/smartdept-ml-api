import numpy as np

# =========================================================
# LINEAR REGRESSION FORECAST
# =========================================================
def linear_forecast(series, future_steps=7):
    if len(series) < 2:
        return [], 0

    x = np.arange(len(series))
    y = np.array(series)

    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs

    future_x = np.arange(len(series), len(series) + future_steps)
    forecast = (slope * future_x + intercept)

    forecast = np.clip(forecast, 0, 1)

    confidence = min(95, abs(slope) * 100 + 70)

    return forecast.tolist(), round(confidence, 2)


# =========================================================
# ROLLING AVERAGE
# =========================================================
def rolling_average(series, window=7):
    if len(series) < window:
        return sum(series) / len(series)

    return np.mean(series[-window:])


# =========================================================
# DROP RISK PROBABILITY
# =========================================================
def drop_probability(history, forecast):
    if not history or not forecast:
        return 0

    last = history[-1]
    next_val = forecast[0]

    drop = last - next_val

    probability = max(0, drop * 100)

    return round(min(probability, 100), 2)


# =========================================================
# LOW STREAK DETECTION
# =========================================================
def detect_low_streak(series, threshold=0.6):
    streak = 0
    for val in reversed(series):
        if val < threshold:
            streak += 1
        else:
            break

    return streak
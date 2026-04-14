# Forecast Model
# This file predicts future attendance trend based on last 30 days data

import numpy as np

def predict_trend(dates, values):

    # convert to numeric timeline
    x = np.arange(len(values))
    y = np.array(values)

    # linear trend slope
    slope = np.polyfit(x, y, 1)[0]

    if slope < -0.02:
        return "DECREASING", abs(slope)
    elif slope > 0.02:
        return "INCREASING", slope
    else:
        return "STABLE", abs(slope)
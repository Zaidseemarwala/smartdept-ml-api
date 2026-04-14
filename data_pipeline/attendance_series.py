# Attendance Series Builder
# This file extracts last 30 days attendance pattern

from datetime import datetime, timedelta

def build_series(attendance_dict, student_index=1):

    today = datetime.today()
    last30 = {}

    for subject in attendance_dict.values():
        for session in subject.values():

            d = datetime.strptime(session["date"], "%Y-%m-%d")

            if (today - d).days <= 30:

                rec = session["records"]
                if len(rec) > student_index:
                    val = 1 if rec[student_index] == "P" else 0
                    last30[d.date()] = val

    # sort by date
    ordered = sorted(last30.items())
    return [v for _, v in ordered]
import pandas as pd

def build_dataset(data):
    rows = []

    for uni in data.values():
        for hod in uni.get("hods", {}).values():
            for dept in hod.get("departments", {}).values():
                for year in dept.get("years", {}).values():
                    for cls in year.get("classes", {}).values():

                        students = cls.get("students", [])
                        attendance = cls.get("attendance", {})

                        # flatten sessions once
                        all_sessions = []
                        for subj in attendance.values():
                            all_sessions.extend(subj.values())

                        for i in range(1, len(students)):
                            student = students[i]
                            if not student:
                                continue

                            total = 0
                            present = 0

                            for session in all_sessions:
                                rec = session.get("records", [])

                                if i < len(rec) and rec[i] in ["P","A"]:
                                    total += 1
                                    if rec[i] == "P":
                                        present += 1

                            percent = round((present / total) * 100, 2) if total else 0

                            rows.append({
                                "id": student.get("roll_no", i),
                                "name": student["name"],
                                "department": dept.get("name"),
                                "year": year.get("name"),
                                "class": cls.get("name"),
                                "attendance": percent,
                                "sessions": total,
                                "absences": total - present,
                                "consistency": present/total if total else 0
                            })

    return pd.DataFrame(rows)
from flask import Flask, request, jsonify
import joblib
import os
from flask_cors import CORS
from models.advanced_forecast import (
    linear_forecast,
    rolling_average,
    drop_probability,
    detect_low_streak
)

from models.forecast_model import predict_trend
from data_pipeline.attendance_series import build_series
from data_pipeline.fetch_data import fetch_all_data
from models.department_predictor import predict_department_future


# =========================================================
# APP SETUP
# =========================================================
app = Flask(__name__)
CORS(app)

MODEL_PATH = "saved_models/model.pkl"
CACHE = None
_model = None


# =========================================================
# LOAD MODEL SAFE
# =========================================================
def load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError("Model not found. Train model first.")
        _model = joblib.load(MODEL_PATH)
    return _model


# =========================================================
# FETCH DATA WITH CACHE
# =========================================================
def get_data():
    global CACHE

    if CACHE is not None:
        return CACHE

try:
    CACHE = fetch_all_data()

    # 🔥 CHECK if data is empty
    if not CACHE:
        raise Exception("No Firebase data")

    print("✅ Using Firebase data")

except Exception as e:
    print("⚠️ Firebase not available, using demo data:", e)

    # 🔥 DEMO DATA
    CACHE = {
        "demo_university": {
            "hods": {
                "hod_1": {
                    "faculty": {
                        "f1": {"name": "Dr. Sharma"},
                        "f2": {"name": "Prof. Khan"}
                    },
                    "departments": {
                        "dept_1": {
                            "years": {
                                "year_1": {
                                    "classes": {
                                        "class_1": {
                                            "name": "CS-A",
                                            "students": [
                                                {"roll_no": "1", "name": "Aman"},
                                                {"roll_no": "2", "name": "Riya"}
                                            ],
                                            "attendance": {
                                                "math": {
                                                    "s1": {
                                                        "records": ["P", "A"],
                                                        "takenBy": {"uid": "f1"}
                                                    },
                                                    "s2": {
                                                        "records": ["P", "P"],
                                                        "takenBy": {"uid": "f1"}
                                                    },
                                                    "s3": {
                                                        "records": ["A", "P"],
                                                        "takenBy": {"uid": "f2"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "classroom": {
                "assignments": {
                    "a1": {
                        "createdBy": "f1",
                        "submissions": [1, 1]
                    }
                }
            }
        }
    }  
   

# =========================================================
# HOME
# =========================================================
@app.route("/")
def home():
    return "AI Server Running"


# =========================================================
# STUDENT RISK PREDICTION
# =========================================================
@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json or {}

        attendance = float(data.get("attendance", 0))
        sessions = int(data.get("sessions", 0))

        absences = sessions - (attendance/100)*sessions
        consistency = attendance/100

        model = load_model()

        pred = model.predict([[attendance, sessions, absences, consistency]])[0]
        prob = model.predict_proba([[attendance, sessions, absences, consistency]])[0][1]

        return jsonify({
            "prediction": "HIGH RISK" if pred == 1 else "SAFE",
            "confidence": round(prob * 100, 2)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/hod-ai-insights")
def hod_ai():
    try:
        hodId = request.args.get("hodId")
        universityId = request.args.get("universityId")

        if not hodId or not universityId:
            return {"error": "hodId and universityId required"}

        data = get_data()
        uni = data.get(universityId, {})

        if "hods" not in uni or hodId not in uni["hods"]:
            return {"error": "Invalid HOD"}

        hod = uni["hods"][hodId]

        department_series = []
        class_forecasts = []
        faculty_performance = []
        faculty_attendance_map = {}

        total_students = 0
        total_classes = 0

        # =====================================================
        # COLLECT ATTENDANCE DATA
        # =====================================================

        for dept in hod.get("departments", {}).values():
            for year in dept.get("years", {}).values():
                for cls in year.get("classes", {}).values():

                    total_classes += 1
                    class_name = cls.get("name", "Class")

                    students = cls.get("students", [])
                    total_students += len([s for s in students if s])

                    session_values = []

                    for subject in cls.get("attendance", {}).values():
                        for session in subject.values():

                            records = session.get("records", [])
                            faculty_id = session.get("takenBy", {}).get("uid")

                            present = sum(1 for r in records if r == "P")
                            total = sum(1 for r in records if r in ["P", "A"])

                            if total == 0:
                                continue

                            val = present / total
                            session_values.append(val)
                            department_series.append(val)

                            if faculty_id:
                                faculty_attendance_map.setdefault(
                                    faculty_id, []
                                ).append(val)

                    if len(session_values) >= 3:
                        recent_avg = sum(session_values[-3:]) / 3
                        overall_avg = sum(session_values) / len(session_values)
                        drop_prob = round(max(0, (overall_avg - recent_avg) * 100), 1)

                        class_forecasts.append({
                            "name": class_name,
                            "riskProbability": drop_prob
                        })

        # =====================================================
        # FACULTY PERFORMANCE
        # =====================================================

        faculty_data = hod.get("faculty", {})

        for fid, series in faculty_attendance_map.items():
            if len(series) < 2:
                continue

            avg_att = sum(series) / len(series)
            attendance_score = avg_att * 100

            consistency_score = max(
                0, 100 - (max(series) - min(series)) * 100
            )

            overall_score = round(
                (0.6 * attendance_score) + (0.4 * consistency_score), 1
            )
            name = faculty_data.get(fid, {}).get("name")
            if not name:
                continue


            faculty_performance.append({
        "facultyId": fid,
        "name": name,
        "attendanceScore": round(attendance_score, 1),
        "consistencyScore": round(consistency_score, 1),
        "overallScore": overall_score
    })

        # =====================================================
        # ASSIGNMENT COMPLIANCE
        # =====================================================

        total_assignments = 0
        total_submissions = 0

        assignments = uni.get("classroom", {}).get("assignments", {})

        for a in assignments.values():
            total_assignments += 1
            submissions = a.get("submissions", [])
            total_submissions += len([s for s in submissions if s])

        submission_percentage = 0
        if total_assignments > 0 and total_students > 0:
            submission_percentage = min(
                100,
                round((total_submissions /
                      (total_assignments * total_students)) * 100, 1)
            )

        # =====================================================
        # DEPARTMENT FORECAST
        # =====================================================

        risk_prob = 0
        if len(department_series) >= 4:
            recent_avg = sum(department_series[-3:]) / 3
            overall_avg = sum(department_series) / len(department_series)
            drop_percent = (overall_avg - recent_avg) * 100
            if drop_percent > 0:
                risk_prob = round(drop_percent, 1)
            else:
                risk_prob = 0

        history = [round(v * 100, 2) for v in department_series[-7:]]

        forecast = []
        if history:
            last = history[-1]
            for i in range(5):
                forecast.append(round(max(0, last - (risk_prob * 0.1 * (i+1))), 2))

        # =====================================================
        # PROFESSIONAL AI PREDICTIONS
        # =====================================================

        ai_predictions = []

        if risk_prob > 5:
            severity = "HIGH" if risk_prob > 15 else "MEDIUM"
            ai_predictions.append({
                "type": "department",
                "severity": severity,
                "message":
                f"Trend regression analysis indicates department attendance may decline by approximately {risk_prob}% over the upcoming week if current momentum persists."
            })

        for cls in class_forecasts:
            if cls["riskProbability"] > 10:
                severity = "HIGH" if cls["riskProbability"] > 25 else "MEDIUM"
                ai_predictions.append({
                    "type": "class",
                    "severity": severity,
                    "message":
                    f"Class {cls['name']} demonstrates attendance instability. Probability of drop is estimated at {cls['riskProbability']}% within the next 5 sessions."
                })

        for f in faculty_performance:
            if f["overallScore"] < 60:
                severity = "HIGH" if f["overallScore"] < 45 else "MEDIUM"
                ai_predictions.append({
                    "type": "faculty",
                    "severity": severity,
                    "message":
                    f"Faculty member {f['name']} is performing below optimal threshold. Current performance index stands at {f['overallScore']}%."
                })

        # =====================================================
        # AI EXECUTIVE SUMMARY
        # =====================================================

        narrative = (
            "Department attendance remains stable with controlled variance."
        )

        if risk_prob > 10:
            narrative = (
                "Department attendance trend indicates measurable downward momentum. Preventive academic intervention is recommended."
            )

        if submission_percentage < 50:
            narrative += " Assignment submission compliance is critically low and requires immediate corrective measures."
        elif submission_percentage < 75:
            narrative += " Assignment compliance shows moderate performance but improvement is advisable."
        else:
            narrative += " Assignment submission compliance remains within acceptable performance thresholds."

        # =====================================================
        # FINAL RESPONSE
        # =====================================================

        return {
            "departmentForecast": {
                "history": history,
                "forecast": forecast,
                "riskProbability": round(risk_prob, 1),
                "confidence": 78,
                "totalStudents": total_students,
                "totalFaculty": len(faculty_data),
                "totalClasses": total_classes
            },
            "classForecasts": class_forecasts,
            "facultyPerformance": faculty_performance,
            "submissionCompliance": {
                "percentage": submission_percentage
            },
            "aiNarrative": narrative,
            "aiPredictions": ai_predictions
        }

    except Exception as e:
        return {"error": str(e)}
    
    

@app.route("/faculty-ai-insights")
def faculty_ai():
    try:
        universityId = request.args.get("universityId")
        hodId = request.args.get("hodId")
        facultyId = request.args.get("facultyId")

        if not universityId or not hodId or not facultyId:
            return {"error": "Missing parameters"}

        data = get_data()
        uni = data.get(universityId, {})
        hod = uni.get("hods", {}).get(hodId, {})

        attendance_series = []
        student_stats = {}
        total_students = set()

        # ======================================================
        # COLLECT FACULTY ATTENDANCE DATA (FIXED)
        # ======================================================

        for dept in hod.get("departments", {}).values():
            for year in dept.get("years", {}).values():
                for cls in year.get("classes", {}).values():

                    students = cls.get("students", [])

                    attendance_map = cls.get("attendance", {})

                    for subject in attendance_map.values():
                        for session in subject.values():

                            taken_by = session.get("takenBy", {})
                            if taken_by.get("uid") != facultyId:
                                continue

                            records = session.get("records", [])

                            # Session level %
                            present = sum(1 for r in records if r == "P")
                            total = sum(1 for r in records if r in ["P", "A"])

                            if total > 0:
                                attendance_series.append(present / total)

                            # Student-level tracking
                            for i, record in enumerate(records):

                                if i >= len(students):
                                    continue

                                raw_student = students[i]
                                if not isinstance(raw_student, dict):
                                    continue

                                student_id = raw_student.get("roll_no")
                                student_name = raw_student.get("name", "Student")

                                if not student_id:
                                    continue

                                total_students.add(student_id)

                                if student_id not in student_stats:
                                    student_stats[student_id] = {
                                        "name": student_name,
                                        "present": 0,
                                        "total": 0,
                                        "streak": 0,
                                        "maxStreak": 0
                                    }

                                if record == "P":
                                    student_stats[student_id]["present"] += 1
                                    student_stats[student_id]["streak"] = 0
                                elif record == "A":
                                    student_stats[student_id]["streak"] += 1
                                    student_stats[student_id]["maxStreak"] = max(
                                        student_stats[student_id]["maxStreak"],
                                        student_stats[student_id]["streak"]
                                    )

                                student_stats[student_id]["total"] += 1

        # ======================================================
        # FORECAST ENGINE
        # ======================================================

        history = [round(v * 100, 2) for v in attendance_series[-7:]]

        risk_probability = 0
        forecast = []
        confidence = 60

        if len(attendance_series) >= 6:
            recent_avg = sum(attendance_series[-3:]) / 3
            older_avg = sum(attendance_series[-6:-3]) / 3

            drop = (older_avg - recent_avg) * 100
            risk_probability = round(max(0, drop), 1)

            last = history[-1] if history else 80

            for i in range(5):
                forecast.append(
                    round(max(0, last - (risk_probability * 0.12 * (i + 1))), 2)
                )

            confidence = min(95, 65 + len(attendance_series) * 2)

        # ======================================================
        # STUDENT RISK ANALYSIS
        # ======================================================

        student_risks = []

        for stats in student_stats.values():

            if stats["total"] == 0:
                continue

            percentage = round(
                (stats["present"] / stats["total"]) * 100, 1
            )

            risk_level = "LOW"

            if percentage < 50 or stats["maxStreak"] >= 3:
                risk_level = "HIGH"
            elif percentage < 70:
                risk_level = "MEDIUM"

            if risk_level != "LOW":
                student_risks.append({
                    "name": stats["name"],
                    "attendance": percentage,
                    "riskLevel": risk_level,
                    "absenceStreak": stats["maxStreak"]
                })

        # ======================================================
        # ASSIGNMENT COMPLIANCE (FIXED)
        # ======================================================

        total_assignments = 0
        total_submissions = 0

        assignments = uni.get("classroom", {}).get("assignments", {})

        for a in assignments.values():

            # FIX: Use createdBy instead of facultyId
            if a.get("createdBy") == facultyId:
                total_assignments += 1
                submissions = a.get("submissions", [])
                total_submissions += len([s for s in submissions if s])

        compliance = 0
        if total_assignments > 0 and len(total_students) > 0:
            compliance = min(
                100,
                round(
                    (total_submissions /
                     (total_assignments * len(total_students))) * 100,
                    1
                )
            )

        # ======================================================
        # GPT-STYLE AI NARRATIVE
        # ======================================================

        avg_attendance = round(sum(attendance_series) /
                               len(attendance_series) * 100, 1) if attendance_series else 0

        narrative = (
            f"Your overall session engagement average stands at {avg_attendance}%. "
        )

        if risk_probability > 0:
            narrative += (
                f"Recent comparative trend modelling indicates a potential decline "
                f"of approximately {risk_probability}% in the upcoming academic cycle "
                f"if attendance volatility persists. "
            )
        else:
            narrative += (
                "Attendance patterns remain stable with no major fluctuations detected. "
            )

        if compliance < 60 and total_assignments > 0:
            narrative += (
                f"Assignment submission compliance currently stands at {compliance}%, "
                "suggesting the need for structured academic reinforcement."
            )

        if student_risks:
            narrative += (
                f" Additionally, {len(student_risks)} students are currently flagged "
                "under academic risk due to low attendance or consecutive absence streaks."
            )

        # ======================================================
        # FINAL RESPONSE
        # ======================================================

        return {
            "facultyForecast": {
                "history": history,
                "forecast": forecast,
                "riskProbability": risk_probability,
                "confidence": confidence,
                "totalStudents": len(total_students),
                "totalSessions": len(attendance_series),
                "averageAttendance": avg_attendance
            },
            "studentRisks": student_risks,
            "assignmentCompliance": {
                "percentage": compliance
            },
            "aiNarrative": narrative
        }

    except Exception as e:
        return {"error": str(e)}

@app.route("/student-ai-insights")
def student_ai():

    try:
        universityId = request.args.get("universityId")
        hodId = request.args.get("hodId")
        departmentId = request.args.get("departmentId")
        yearId = request.args.get("yearId")
        classId = request.args.get("classId")
        studentId = request.args.get("studentId")

        if not all([universityId, hodId, departmentId, yearId, classId, studentId]):
            return {"error": "Missing parameters"}

        data = get_data()
        uni = data.get(universityId, {})
        hod = uni.get("hods", {}).get(hodId, {})
        dept = hod.get("departments", {}).get(departmentId, {})
        year = dept.get("years", {}).get(yearId, {})
        cls = year.get("classes", {}).get(classId, {})

        students = cls.get("students", [])
        attendance_series = []

        # =====================================================
        # FIND STUDENT INDEX
        # =====================================================

        student_index = None
        student_name = "Student"

        for i, s in enumerate(students):
            if isinstance(s, dict):
                if str(s.get("roll_no")) == str(studentId):
                    student_index = i
                    student_name = s.get("name", "Student")
                    break

        if student_index is None:
            return {"error": f"Student with roll_no {studentId} not found"}

        # =====================================================
        # COLLECT ATTENDANCE DATA (SORTED)
        # =====================================================

        for subject in cls.get("attendance", {}).values():

            sessions = sorted(
                subject.values(),
                key=lambda x: x.get("createdAt", 0)
            )

            for session in sessions:

                records = session.get("records", [])

                if student_index >= len(records):
                    continue

                record = records[student_index]

                if record in ["P", "A"]:
                    attendance_series.append(1 if record == "P" else 0)

        if not attendance_series:
            return {"error": "No attendance records"}

        # =====================================================
        # BASIC CALCULATIONS
        # =====================================================

        total_sessions = len(attendance_series)
        present_count = sum(attendance_series)

        overall_attendance = round(
            (present_count / total_sessions) * 100, 1
        )

        history = [round(v * 100, 2) for v in attendance_series]

        # =====================================================
        # TREND CALCULATION
        # =====================================================

        risk_probability = 0
        improvement_probability = 0
        confidence = 65

        if len(attendance_series) >= 6:

            recent_avg = sum(attendance_series[-3:]) / 3
            older_avg = sum(attendance_series[-6:-3]) / 3

            change = (recent_avg - older_avg) * 100

            if change < 0:
                risk_probability = round(abs(change), 1)
            else:
                improvement_probability = round(change, 1)

            confidence = min(95, 65 + len(attendance_series) * 2)

        # =====================================================
        # FORECAST NEXT 5 SESSIONS
        # =====================================================

        forecast = []

        last = history[-1]

        for i in range(5):

            if risk_probability > 0:
                next_val = last - (risk_probability * 0.15 * (i + 1))

            elif improvement_probability > 0:
                next_val = last + (improvement_probability * 0.12 * (i + 1))

            else:
                next_val = last

            forecast.append(round(max(0, min(100, next_val)), 2))

        future_projection = forecast[-1]

        # =====================================================
        # PERFORMANCE BAND
        # =====================================================

        if overall_attendance >= 85:
            performance_band = "excellent"
        elif overall_attendance >= 75:
            performance_band = "strong"
        elif overall_attendance >= 60:
            performance_band = "moderate"
        else:
            performance_band = "critical"

        trend_direction = "STABLE"

        if risk_probability > 0:
            trend_direction = "DECREASING"
        elif improvement_probability > 0:
            trend_direction = "INCREASING"

        # =====================================================
        # AI NARRATIVE
        # =====================================================

        narrative = (
            f"{student_name}, your current overall attendance stands at "
            f"{overall_attendance}%, placing you in the {performance_band} "
            f"academic performance category. "
        )

        if trend_direction == "INCREASING":

            narrative += (
                f"Recent session analysis shows an improvement of approximately "
                f"{improvement_probability}% compared with earlier attendance patterns. "
                f"If this positive momentum continues, your attendance could reach "
                f"around {future_projection}% in the upcoming academic sessions. "
                "Maintaining regular participation will further strengthen your academic stability."
            )

        elif trend_direction == "DECREASING":

            narrative += (
                f"Trend analysis indicates a decline of approximately "
                f"{risk_probability}% when compared with earlier sessions. "
                f"If the current pattern continues, your attendance may decrease "
                f"to approximately {future_projection}% in the upcoming sessions. "
                "Avoiding consecutive absences and improving class participation "
                "will help stabilise this trend."
            )

        else:

            narrative += (
                "Attendance patterns currently appear stable with no major "
                f"changes detected. Forecast modelling indicates your attendance "
                f"will remain around {future_projection}% over the next few sessions."
            )

        if overall_attendance < 60:
            narrative += (
                " However, your overall attendance is below the recommended "
                "academic threshold and requires immediate improvement."
            )

        # =====================================================
        # AI PREDICTIONS
        # =====================================================

        ai_predictions = []

        if risk_probability > 5:
            ai_predictions.append({
                "type": "attendance",
                "severity": "HIGH" if risk_probability > 15 else "MEDIUM",
                "message":
                f"Attendance may decline by approximately {risk_probability}% if corrective action is not taken."
            })

        if improvement_probability > 5:
            ai_predictions.append({
                "type": "growth",
                "severity": "POSITIVE",
                "message":
                f"Attendance is projected to improve by approximately {improvement_probability}% if current consistency continues."
            })

        if overall_attendance < 60:
            ai_predictions.append({
                "type": "risk",
                "severity": "HIGH",
                "message":
                "Overall attendance is currently below recommended academic standards."
            })

        # =====================================================
        # FINAL RESPONSE
        # =====================================================

        return {
            "studentForecast": {
                "history": history[-7:],
                "forecast": forecast,
                "overallAttendance": overall_attendance,
                "riskProbability": risk_probability,
                "improvementProbability": improvement_probability,
                "confidence": confidence,
                "trend": trend_direction,
                "performanceBand": performance_band,
                "predictionText":
                    "Attendance improving"
                    if improvement_probability > 0
                    else "Attendance likely to decrease"
                    if risk_probability > 0
                    else "Attendance stable"
            },
            "aiPredictions": ai_predictions,
            "aiNarrative": narrative
        }

    except Exception as e:
        return {"error": str(e)}

@app.route("/forecast")
def forecast():

    try:
        universityId = request.args.get("universityId")

        data = get_data()
        uni = data.get(universityId, {})

        classroom = uni.get("classroom", {})
        years = classroom.get("years", {})

        first_year = next(iter(years.values()), {})
        first_class = next(iter(first_year.get("classes", {}).values()), {})

        attendance = first_class.get("attendance", {})
        series = build_series(attendance)

        if len(series) < 2:
            return {"trend": "Not enough data", "series": [], "confidence": 0}

        trend, strength = predict_trend(range(len(series)), series)

        return {
            "trend": trend,
            "confidence": round(strength, 3),
            "series": series[-7:]
        }

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
    
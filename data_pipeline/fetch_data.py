import firebase_admin
from firebase_admin import credentials, db

FIREBASE_AVAILABLE = False

# ======================================================
# SAFE INITIALIZATION (NO CRASH)
# ======================================================
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("config/firebase_key.json")
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://smartdept-5bf42-default-rtdb.firebaseio.com/"
        })
        FIREBASE_AVAILABLE = True
        print("✅ Firebase connected")

except Exception as e:
    print("⚠️ Firebase not available:", e)
    FIREBASE_AVAILABLE = False


# ======================================================
# FETCH DATA (SAFE)
# ======================================================
def fetch_all_data(university_id=None):
    try:
        if not FIREBASE_AVAILABLE:
            print("⚠️ Using fallback (no Firebase)")
            return {}

        ref = db.reference("universities")

        if university_id:
            data = ref.child(university_id).get()
            if data:
                return {university_id: data}
            return {}

        data = ref.get()
        if not data:
            return {}

        return data

    except Exception as e:
        print("Firebase fetch error:", e)
        return {}
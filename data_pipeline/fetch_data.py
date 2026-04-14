import firebase_admin
from firebase_admin import credentials, db

# Initialize only once
if not firebase_admin._apps:
    cred = credentials.Certificate("config/firebase_key.json")
    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://smartdept-5bf42-default-rtdb.firebaseio.com/"
    })


def fetch_all_data(university_id=None):
    try:
        ref = db.reference("universities")

        # 🔥 Fetch single university directly (recommended)
        if university_id:
            data = ref.child(university_id).get()
            if data:
                return {university_id: data}
            return {}

        # 🔥 Fetch all universities
        data = ref.get()
        if not data:
            return {}

        return data

    except Exception as e:
        print("Firebase fetch error:", e)
        return {}
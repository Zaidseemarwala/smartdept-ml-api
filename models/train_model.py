from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import os


def train(df):

    # create label
    df["risk"] = df["attendance"].apply(lambda x: 1 if x < 65 else 0)

    # features
    X = df[[
        "attendance",
        "sessions",
        "absences",
        "consistency"
    ]]
    y = df["risk"]

    # split
    X_train,X_test,y_train,y_test = train_test_split(
        X,y,test_size=0.2,random_state=42
    )

   
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        random_state=42
    )

    model.fit(X_train,y_train)

    
    pred = model.predict(X_test)
    print("Accuracy:",accuracy_score(y_test,pred))

    
    os.makedirs("saved_models",exist_ok=True)
    joblib.dump(model,"saved_models/model.pkl")

    print("Model trained & saved")
"""Train Random Forest loan approval classifier on the Kaggle dataset."""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


BASE_DIR = Path(__file__).parent
DATASET_PATH = BASE_DIR / "loan_approval_dataset.csv"
MODEL_PATH = BASE_DIR / "loan_model.pkl"


def train_and_save(verbose: bool = True):
    df = pd.read_csv(DATASET_PATH)
    df.columns = df.columns.str.strip()
    for column in df.select_dtypes(include=["object"]).columns:
        df[column] = df[column].str.strip()

    features = [
        "no_of_dependents",
        "education",
        "self_employed",
        "income_annum",
        "loan_amount",
        "loan_term",
        "cibil_score",
        "residential_assets_value",
        "commercial_assets_value",
        "luxury_assets_value",
        "bank_asset_value",
    ]
    target = "loan_status"

    X = df[features]
    y = df[target]

    numerical_features = [
        "no_of_dependents",
        "income_annum",
        "loan_amount",
        "loan_term",
        "cibil_score",
        "residential_assets_value",
        "commercial_assets_value",
        "luxury_assets_value",
        "bank_asset_value",
    ]
    categorical_features = ["education", "self_employed"]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numerical",
                Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))]),
                numerical_features,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )

    model_pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=250,
                    max_depth=12,
                    min_samples_leaf=2,
                    random_state=42,
                    class_weight="balanced",
                    n_jobs=-1,
                ),
            ),
        ]
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    if verbose:
        print("Training Random Forest loan approval model on Kaggle dataset...")

    model_pipeline.fit(X_train, y_train)
    predictions = model_pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)

    if verbose:
        print(f"Model accuracy: {accuracy:.2%}")
        print("\nClassification report:")
        print(classification_report(y_test, predictions))
        print("Confusion matrix:")
        print(confusion_matrix(y_test, predictions))

    joblib.dump(model_pipeline, MODEL_PATH)

    if verbose:
        print(f"\nModel saved successfully at: {MODEL_PATH}")

    return {
        "accuracy": float(accuracy),
        "model_path": str(MODEL_PATH),
        "train_size": len(X_train),
        "test_size": len(X_test),
    }


if __name__ == "__main__":
    train_and_save(verbose=True)

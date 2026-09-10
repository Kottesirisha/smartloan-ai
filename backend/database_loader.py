import pandas as pd
from pathlib import Path


DATASET_PATH = Path(__file__).parent / "loan_approval_dataset.csv"


def load_loan_dataset():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {DATASET_PATH}"
        )

    df = pd.read_csv(DATASET_PATH)

    # Remove unwanted spaces from column names
    df.columns = df.columns.str.strip()

    return df


def find_loan_record(loan_id):
    df = load_loan_dataset()

    record = df[df["loan_id"] == int(loan_id)]

    if record.empty:
        return None

    return record.iloc[0].to_dict()


def compare_with_dataset(
    loan_id,
    annual_income,
    loan_amount
):
    dataset_record = find_loan_record(loan_id)

    if dataset_record is None:
        return {
            "matched": False,
            "reason": "Loan ID was not found in the Kaggle dataset."
        }

    income_difference = abs(
        float(dataset_record["income_annum"]) - float(annual_income)
    )

    loan_difference = abs(
        float(dataset_record["loan_amount"]) - float(loan_amount)
    )

    return {
        "matched": True,
        "loan_id": int(dataset_record["loan_id"]),
        "dataset_income": float(dataset_record["income_annum"]),
        "applicant_income": float(annual_income),
        "income_difference": income_difference,
        "dataset_loan_amount": float(dataset_record["loan_amount"]),
        "requested_loan_amount": float(loan_amount),
        "loan_difference": loan_difference,
        "cibil_score": int(dataset_record["cibil_score"]),
        "dataset_status": dataset_record["loan_status"],
        "education": dataset_record["education"],
        "self_employed": dataset_record["self_employed"],
    }


if __name__ == "__main__":
    df = load_loan_dataset()

    print("Dataset loaded successfully!")
    print("Dataset path:", DATASET_PATH)
    print("Number of records:", len(df))
    print("Columns:", df.columns.tolist())

    print("\nFirst five records:")
    print(df.head())

    print("\nSample loan record:")
    print(find_loan_record(1))
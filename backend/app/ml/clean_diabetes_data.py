"""Data cleaning, validation, and preparation script for the diabetes dataset."""
from pathlib import Path
import pandas as pd
import json

RAW_PATH = Path(__file__).resolve().parents[2] / "datasets" / "diabetes" / "raw" / "diabetes.csv"
PROCESSED_PATH = Path(__file__).resolve().parents[2] / "datasets" / "diabetes" / "processed" / "cleaned_diabetes.csv"
METADATA_PATH = Path(__file__).resolve().parents[2] / "datasets" / "diabetes" / "processed" / "dataset_metadata.json"


def clean_and_prepare_dataset():
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw dataset not found at {RAW_PATH}")

    df = pd.read_csv(RAW_PATH)
    initial_rows = len(df)

    # 1. Check schema
    expected_columns = [
        "gender", "age", "hypertension", "heart_disease",
        "smoking_history", "bmi", "HbA1c_level", "blood_glucose_level", "diabetes"
    ]
    assert all(col in df.columns for col in expected_columns), f"Missing columns: {set(expected_columns) - set(df.columns)}"

    # 2. Check for missing values
    null_counts = df.isnull().sum().to_dict()

    # 3. Handle duplicates
    duplicate_count = int(df.duplicated().sum())

    # 4. Validate categorical domains
    valid_genders = ["Female", "Male", "Other"]
    valid_smoking = ["No Info", "never", "former", "current", "not current", "ever"]
    
    # Filter or retain standard values
    cleaned_df = df[
        df["gender"].isin(valid_genders) &
        df["smoking_history"].isin(valid_smoking) &
        (df["age"] >= 0) & (df["age"] <= 120) &
        (df["bmi"] >= 8.0) & (df["bmi"] <= 100.0) &
        (df["HbA1c_level"] >= 3.0) & (df["HbA1c_level"] <= 20.0) &
        (df["blood_glucose_level"] >= 40) & (df["blood_glucose_level"] <= 600) &
        df["hypertension"].isin([0, 1]) &
        df["heart_disease"].isin([0, 1]) &
        df["diabetes"].isin([0, 1])
    ].copy()

    # Ensure processed directory exists
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned_df.to_csv(PROCESSED_PATH, index=False)

    metadata = {
        "raw_path": str(RAW_PATH),
        "processed_path": str(PROCESSED_PATH),
        "initial_rows": initial_rows,
        "cleaned_rows": len(cleaned_df),
        "null_counts": null_counts,
        "duplicate_count": duplicate_count,
        "target_distribution": {
            "non_diabetic_0": int((cleaned_df["diabetes"] == 0).sum()),
            "diabetic_1": int((cleaned_df["diabetes"] == 1).sum()),
            "prevalence_rate": float(cleaned_df["diabetes"].mean())
        },
        "features": {
            "numerical": ["age", "bmi", "HbA1c_level", "blood_glucose_level"],
            "binary": ["hypertension", "heart_disease"],
            "categorical": {
                "gender": list(cleaned_df["gender"].unique()),
                "smoking_history": list(cleaned_df["smoking_history"].unique())
            }
        }
    }

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Dataset successfully cleaned and saved to {PROCESSED_PATH}")
    print(f"Retained {len(cleaned_df)} of {initial_rows} records.")
    return metadata


if __name__ == "__main__":
    clean_and_prepare_dataset()

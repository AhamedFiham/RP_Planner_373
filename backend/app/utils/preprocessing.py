"""Feature preprocessing pipeline and transformers for diabetes risk prediction."""
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Supported feature names in expected order
NUMERICAL_FEATURES = ["age", "bmi", "HbA1c_level", "blood_glucose_level"]
BINARY_FEATURES = ["hypertension", "heart_disease"]
CATEGORICAL_FEATURES = ["gender", "smoking_history"]

ALL_FEATURE_COLUMNS = NUMERICAL_FEATURES + BINARY_FEATURES + CATEGORICAL_FEATURES


def build_preprocessor() -> ColumnTransformer:
    """Creates a ColumnTransformer to handle numerical scaling and categorical one-hot encoding."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERICAL_FEATURES),
            ("bin", "passthrough", BINARY_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return preprocessor


def get_feature_names(fitted_preprocessor: ColumnTransformer) -> list[str]:
    """Extracts cleaned output feature names from the fitted preprocessor."""
    try:
        return list(fitted_preprocessor.get_feature_names_out())
    except Exception:
        # Fallback if get_feature_names_out is not available
        names = list(NUMERICAL_FEATURES) + list(BINARY_FEATURES)
        cat_encoder = fitted_preprocessor.named_transformers_["cat"]
        if hasattr(cat_encoder, "get_feature_names_out"):
            cat_names = list(cat_encoder.get_feature_names_out(CATEGORICAL_FEATURES))
            names.extend(cat_names)
        return names

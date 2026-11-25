"""Train a RandomForestClassifier on the animal shelter dataset."""

import joblib
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from animal_shelter.data import load_data
from animal_shelter.features import add_features

CAT_FEATURES = ["animal_type", "is_dog", "has_name", "sex", "neutered", "hairtype"]
NUM_FEATURES = ["days_upon_outcome"]
TARGET = "outcome_type"


def train(input_path: str, output_path: str) -> Pipeline:
    """Train a RandomForestClassifier on the animal shelter dataset.

    Args:
        input_path (str): Path to the input data file.
        output_path (str): Path to save the trained model.

    Returns
    -------
        Pipeline: Trained RandomForestClassifier pipeline.
    """
    raw_data = load_data(input_path)
    with_features = add_features(raw_data)

    X = with_features[CAT_FEATURES + NUM_FEATURES]
    y = with_features[TARGET]

    clf_model = build_pipeline()
    clf_model.fit(X, y)

    joblib.dump(clf_model, output_path)

    return clf_model


def build_pipeline() -> Pipeline:
    """Build a RandomForestClassifier pipeline with preprocessing features.

    Returns
    -------
        Pipeline: Configured RandomForestClassifier pipeline.
    """
    num_transformer = Pipeline(
        steps=[("imputer", SimpleImputer()), ("scaler", StandardScaler())]
    )
    cat_transformer = Pipeline(steps=[("onehot", OneHotEncoder(drop="first"))])
    transformer = ColumnTransformer(
        (
            ("numeric", num_transformer, NUM_FEATURES),
            ("categorical", cat_transformer, CAT_FEATURES),
        )
    )

    clf_model = Pipeline(
        [("transformer", transformer), ("model", RandomForestClassifier())]
    )

    return clf_model

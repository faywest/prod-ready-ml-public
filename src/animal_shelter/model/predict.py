"""Predict outcomes using a trained RandomForestClassifier."""

import joblib

from animal_shelter.data import load_data
from animal_shelter.features import add_features
from animal_shelter.model.train import CAT_FEATURES, NUM_FEATURES


def predict(input_path: str, model_path: str):
    """Predict outcomes using a trained RandomForestClassifier.

    Args:
        input_path (str): Path to the input data file.
        model_path (str): Path to the trained model file.

    Returns
    -------
        np.ndarray: Predicted outcomes.
    """
    test_data = load_data(input_path)
    with_features = add_features(test_data)
    X_test = with_features[CAT_FEATURES + NUM_FEATURES]
    clf_model = joblib.load(model_path)
    predictions = clf_model.predict(X_test)
    return predictions

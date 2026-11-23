import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal

from animal_shelter import features


def test_check_has_name():
    s = pd.Series(["Ivo", "Henk", "unknown"])
    result = features._check_has_name(s)
    expected = pd.Series([True, True, False])
    assert_series_equal(result, expected)


def test_check_is_dog():
    s = pd.Series(["Dog", "Cat", "dog", "CAT"])
    result = features._check_is_dog(s)
    expected = pd.Series([True, False, True, False])
    assert_series_equal(result, expected)


def test_get_sex():
    s = pd.Series(["Neutered Male", "Spayed Female", "Intact Male", "Unknown"])
    result = features._get_sex(s)
    expected = pd.Series(["male", "female", "male", "unknown"])
    assert_series_equal(result, expected)


def test_get_neutered():
    s = pd.Series(["Neutered Male", "Spayed Female", "Intact Female", "Unknown"])
    result = features._get_neutered(s)
    expected = pd.Series(["fixed", "fixed", "intact", "unknown"])
    assert_series_equal(result, expected)


def test_get_hair_type():
    s = pd.Series(
        [
            "Domestic Shorthair Mix",
            "Domestic Medium Hair",
            "Domestic Longhair Mix",
            "Labrador Retriever Mix",
        ]
    )
    result = features._get_hair_type(s)
    expected = pd.Series(["shorthair", "medium hair", "longhair", "unknown"])
    assert_series_equal(result, expected)


def test_compute_days_upon_outcome():
    s = pd.Series(["1 year", "2 years", "3 weeks", "1 month", "5 days", "Unknown"])
    result = features._compute_days_upon_outcome(s)
    expected = pd.Series([365.0, 730.0, 21.0, 30.0, 5.0, np.nan])
    assert_series_equal(result, expected)

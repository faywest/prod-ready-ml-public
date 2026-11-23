import pytest

from animal_shelter import data


def test_convert_camel_case():
    assert data.convert_camel_case("CamelCase") == "camel_case"
    assert data.convert_camel_case("CamelCASE") == "camel_case"
    assert data.convert_camel_case("camel-case") != "camel_case"
    assert data.convert_camel_case("camel_case") == "camel_case"


def test_convert_camel_case_raises_for_non_string():
    with pytest.raises(TypeError):
        data.convert_camel_case(123)
    with pytest.raises(TypeError):
        data.convert_camel_case(None)

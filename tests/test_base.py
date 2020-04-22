from datamodel_code_generator.parser.base import snake_to_upper_camel


def test_snake_to_upper_camel_underscore():
    """In case a name starts with a underline, we should keep it."""
    assert snake_to_upper_camel('_hello') == '_Hello'

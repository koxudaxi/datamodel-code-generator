from __future__ import annotations

from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.model.django import DataModelField, DjangoModel
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType


def test_django_model() -> None:
    field = DataModelField(name="name", data_type=DataType(type="str"), required=True)

    django_model = DjangoModel(
        fields=[field],
        reference=Reference(name="test_model", path="test_model"),
    )

    assert django_model.name == "test_model"
    assert django_model.fields == [field]
    assert django_model.decorators == []
    assert "class test_model(models.Model):" in django_model.render()
    assert "name = models.CharField(max_length=255)" in django_model.render()


def test_django_field_types() -> None:
    # Test string field
    str_field = DataModelField(name="title", data_type=DataType(type="str"), required=True)
    assert str_field.django_field_type == "models.CharField"
    assert "max_length=255" in str_field.django_field_options

    # Test integer field
    int_field = DataModelField(name="count", data_type=DataType(type="int"), required=True)
    assert int_field.django_field_type == "models.IntegerField"

    # Test boolean field
    bool_field = DataModelField(name="active", data_type=DataType(type="bool"), required=False)
    assert bool_field.django_field_type == "models.BooleanField"
    assert "null=True" in bool_field.django_field_options
    assert "blank=True" in bool_field.django_field_options


def test_django_email_field() -> None:
    # Test email field detection by name
    email_field = DataModelField(name="email", data_type=DataType(type="str"), required=True)
    assert email_field.django_field_type == "models.EmailField"
    assert "max_length=255" in email_field.django_field_options


def test_django_datetime_field() -> None:
    # Test datetime field detection by name
    datetime_field = DataModelField(name="created_at", data_type=DataType(type="str"), required=False)
    assert datetime_field.django_field_type == "models.DateTimeField"
    assert "null=True" in datetime_field.django_field_options
    assert "blank=True" in datetime_field.django_field_options


def test_django_field_generation() -> None:
    # Test required field
    required_field = DataModelField(name="title", data_type=DataType(type="str"), required=True)
    assert required_field.field == "models.CharField(max_length=255)"

    # Test optional field
    optional_field = DataModelField(name="description", data_type=DataType(type="str"), required=False)
    assert optional_field.field == "models.CharField(null=True, blank=True, max_length=255)"


def test_django_field_help_text() -> None:
    # Test field with description (help_text)
    field_with_description = DataModelField(
        name="disposition",
        data_type=DataType(type="str"),
        required=False,
        extras={"description": "The state that a message should be left in after it has been forwarded."}
    )
    assert "help_text='The state that a message should be left in after it has been forwarded.'" in field_with_description.django_field_options
    assert "help_text='The state that a message should be left in after it has been forwarded.'" in field_with_description.field

    # Test field with description containing single quotes
    field_with_quotes = DataModelField(
        name="email_address",
        data_type=DataType(type="str"),
        required=False,
        extras={"description": "Email address to which all incoming messages are forwarded. This email address must be a verified member of the forwarding addresses."}
    )
    expected_help_text = "help_text='Email address to which all incoming messages are forwarded. This email address must be a verified member of the forwarding addresses.'"
    assert expected_help_text in field_with_quotes.django_field_options

    # Test field with description containing single quotes that need escaping
    field_with_escaped_quotes = DataModelField(
        name="test_field",
        data_type=DataType(type="str"),
        required=False,
        extras={"description": "This is a 'test' description with quotes."}
    )
    expected_escaped_help_text = "help_text='This is a \\'test\\' description with quotes.'"
    assert expected_escaped_help_text in field_with_escaped_quotes.django_field_options

    # Test field without description (no help_text)
    field_without_description = DataModelField(
        name="simple_field",
        data_type=DataType(type="str"),
        required=False
    )
    assert "help_text" not in field_without_description.django_field_options


def test_django_model_with_help_text() -> None:
    # Test complete Django model generation with help_text
    disposition_field = DataModelField(
        name="disposition",
        data_type=DataType(type="str"),
        required=False,
        extras={"description": "The state that a message should be left in after it has been forwarded."}
    )

    email_field = DataModelField(
        name="email_address",
        data_type=DataType(type="str"),
        required=False,
        extras={"description": "Email address to which all incoming messages are forwarded. This email address must be a verified member of the forwarding addresses."}
    )

    enabled_field = DataModelField(
        name="enabled",
        data_type=DataType(type="bool"),
        required=False,
        extras={"description": "Whether all incoming mail is automatically forwarded to another address."}
    )

    django_model = DjangoModel(
        fields=[disposition_field, email_field, enabled_field],
        reference=Reference(name="AutoForwarding", path="AutoForwarding"),
        description="Auto-forwarding settings for an account."
    )

    rendered = django_model.render()

    # Check that the model class and description are rendered correctly
    assert "class AutoForwarding(models.Model):" in rendered
    assert "Auto-forwarding settings for an account." in rendered

    # Check that fields with help_text are rendered correctly
    assert "disposition = models.CharField(null=True, blank=True, max_length=255, help_text='The state that a message should be left in after it has been forwarded.')" in rendered
    assert "email_address = models.EmailField(null=True, blank=True, max_length=255, help_text='Email address to which all incoming messages are forwarded. This email address must be a verified member of the forwarding addresses.')" in rendered
    assert "enabled = models.BooleanField(null=True, blank=True, help_text='Whether all incoming mail is automatically forwarded to another address.')" in rendered

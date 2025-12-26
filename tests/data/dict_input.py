"""Dict input schemas for testing generate() with dict input."""

from __future__ import annotations

jsonschema_dict: dict[str, object] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
    },
    "required": ["name"],
}

openapi_dict: dict[str, object] = {
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "paths": {},
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            }
        }
    },
}

auto_error_dict: dict[str, object] = {
    "type": "object",
    "properties": {"foo": {"type": "string"}},
}

graphql_error_dict: dict[str, object] = {
    "type": "object",
    "properties": {"bar": {"type": "string"}},
}

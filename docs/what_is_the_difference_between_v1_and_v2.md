# What is the difference between pydantic v1 and v2 output model? 

## Summary
datamodel-code-generator supports Pydantic v1 and v2 as output model type.

Pydantic v2 is a major release with many breaking changes. See the migration guide for more information:
https://docs.pydantic.dev/2.0/migration/

## What's changes in v2 output?
### `__root__` field (a.k.a [Custom Root Types](https://docs.pydantic.dev/1.10/usage/models/#custom-root-types))
`__root__` field (a.k.a [Custom Root Types](https://docs.pydantic.dev/1.10/usage/models/#custom-root-types)) is removed in pydantic v2.
The model is changed to [RootModel](https://docs.pydantic.dev/latest/usage/models/#rootmodel-and-custom-root-types)

### pydantic.Field
https://docs.pydantic.dev/2.0/migration/#changes-to-pydanticfield

- const -> removed
- min_items (use min_length instead)
- max_items (use max_length instead)
- unique_items -> removed and the list type will be replaced by `typing.Set`. this feature is discussed in https://github.com/pydantic/pydantic-core/issues/296
- allow_mutation (use frozen instead)
- regex (use pattern instead)

### Model Config
- `pydantic.Config` -> `pydantic.ConfigDict` 
- allow_mutation —> frozen (inverse value for getting same behavior).
- allow_population_by_field_name → populate_by_name


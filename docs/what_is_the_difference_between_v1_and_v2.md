# 🔄 What is the difference between pydantic v1 and v2 output model?

## 📋 Summary

datamodel-code-generator supports Pydantic v1 and v2 as output model types.

Pydantic v2 is a major release with many breaking changes. See the [migration guide](https://docs.pydantic.dev/2.0/migration/) for more information.

## ✨ What's changed in v2 output?

### 📦 `__root__` field (Custom Root Types)

`__root__` field (a.k.a [Custom Root Types](https://docs.pydantic.dev/1.10/usage/models/#custom-root-types)) is removed in pydantic v2.
The model is changed to [RootModel](https://docs.pydantic.dev/latest/usage/models/#rootmodel-and-custom-root-types).

### 🔧 pydantic.Field

See [Changes to pydantic.Field](https://docs.pydantic.dev/2.0/migration/#changes-to-pydanticfield) for details.

| v1 | v2 | Notes |
|----|----|----|
| `const` | ❌ removed | |
| `min_items` | `min_length` | |
| `max_items` | `max_length` | |
| `unique_items` | ❌ removed | List type replaced by `typing.Set`. See [pydantic-core#296](https://github.com/pydantic/pydantic-core/issues/296) |
| `allow_mutation` | `frozen` | Inverse value |
| `regex` | `pattern` | |

### ⚙️ Model Config

| v1 | v2 |
|----|----|
| `pydantic.Config` | `pydantic.ConfigDict` |
| `allow_mutation` | `frozen` (inverse value) |
| `allow_population_by_field_name` | `populate_by_name` |

---

## 📖 See Also

- 🖥️ [CLI Reference: `--output-model-type`](cli-reference/model-customization.md#output-model-type) - Select Pydantic v1 or v2 output
- ⚙️ [CLI Reference: Model Customization](cli-reference/model-customization.md) - All model generation options

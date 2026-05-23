# Schema-Derived Payload Validation Future Work

This file tracks schemas that the payload-validation e2e test intentionally does not
run yet. These cases are not simple fixture omissions. They need either better
payload generation, an explicit backend compatibility policy, or a careful
generator change that avoids surprising existing users.

## Payload Generator Limitations

The following cases have valid payloads in principle, but `hypothesis-jsonschema`
does not currently generate them reliably from the raw schema shape:

- `jsonschema/all_of_any_of_base_class_ref.json`
- `openapi/allof.yaml::components.schemas.AllOfNested3`
- `openapi/allof_with_required_inherited_complex_allof.yaml::components.schemas.ProjectedItem`
- `openapi/allof_with_required_inherited_comprehensive.yaml::components.schemas.Entity`
- `openapi/allof_with_required_inherited_comprehensive.yaml::components.schemas.ProjectedEntity`
- `openapi/allof_with_required_inherited_coverage.yaml::components.schemas.EdgeCasesCoverage`
- `openapi/allof_with_required_inherited_edge_cases.yaml::components.schemas.EdgeCases`
- `openapi/allof_with_required_inherited_edge_cases.yaml::components.schemas.ProjectedEdgeCases`

These schemas combine `allOf`, inherited required fields, nested references, and
union keywords in ways that often cause filtered strategies to become
unsatisfiable or flaky. The generator may still have bugs in this area, but the
current blocker is that the e2e test cannot reliably obtain schema-valid inputs.

Future work:

- Add schema normalization for inherited `allOf` shapes before calling
  `hypothesis-jsonschema`, while still validating generated payloads against the
  original schema.
- Keep any normalization local to payload generation. It must not weaken the
  source-schema validation step.
- Re-enable excluded cases one by one when deterministic valid payload generation
  is available.

## OpenAPI Discriminator Compatibility Policy

The following cases expose a mismatch between OpenAPI discriminator semantics,
JSON Schema validation semantics, and backend-specific runtime validators:

- `openapi/discriminator.yaml::components.schemas.Demo`
- `openapi/discriminator_float_mapping.yaml::components.schemas.Base`
- `openapi/discriminator_in_array_oneof.yaml::components.schemas.Demo`
- `openapi/discriminator_without_mapping.yaml::components.schemas.Demo`

These are not safe to change as incidental fixes in the payload-validation test
work. Existing users may rely on the current generated type shape, especially for
Pydantic discriminated unions.

Important distinctions:

- OpenAPI discriminator mapping keys are strings, but the discriminator property
  schema can be numeric or otherwise constrained. For example, a mapping key
  `"1.5"` can point to a schema whose discriminator field is `type: number`.
- Without an explicit mapping, OpenAPI uses implicit schema-name-based mapping.
  That can conflict with a JSON Schema `enum` on the discriminator property.
- For `allOf` inheritance and array item unions, mapping tags can be applied at a
  different semantic level than the inherited JSON Schema constraints.
- Pydantic v2 discriminated unions require literal discriminator values. Other
  output backends may need a different representation or may not support the
  same semantics.

Future work:

- Decide whether existing default output should continue to prioritize OpenAPI
  discriminator semantics, or whether a schema-faithful mode should fall back to
  plain unions when discriminator tags conflict with field constraints.
- Consider using an existing strict/schema-version mode or adding a dedicated
  compatibility option before changing default behavior.
- If a generated Pydantic model is runtime-invalid, fix it directly. If the model
  is runtime-valid but chooses OpenAPI discriminator semantics over JSON Schema
  validation semantics, treat behavior changes as compatibility-sensitive.
- Add backend-specific tests when enabling any excluded discriminator case. A
  change that is correct for Pydantic may not be correct for dataclasses,
  TypedDict, msgspec, or other output types.

## Top-Level Nullable Object Components

The following case is excluded:

- `openapi/ref_nullable.yaml::components.schemas.NullableChild`

The component schema is a nullable object, so `null` is schema-valid for the
component itself. The current class-based output represents the object component
as a model class:

```python
class NullableChild(BaseModel):
    name: str | None = None
```

That class does not validate `None` when used directly. Nullable references to
the component can still be represented in parent fields, and the payload e2e test
covers that through `openapi/ref_nullable.yaml::components.schemas.Parent`.

Future work:

- Decide whether top-level nullable object components should produce an
  additional wrapper/root type for direct validation of `null`.
- Treat a default output change as compatibility-sensitive, because it can change
  class names, exported types, annotations, and user imports.
- Consider limiting any new behavior to a schema-faithful or strict nullable mode
  if preserving existing class-based output is more important for default usage.

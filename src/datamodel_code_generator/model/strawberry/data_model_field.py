from __future__ import annotations

from datamodel_code_generator.model.base import DataModelFieldBase


class DataModelField(DataModelFieldBase):
    @property
    def field(self) -> str | None:
        """Generate strawberry.field(name='...') for reserved keyword fields."""
        # Check if field name was changed due to being a reserved keyword
        if (
            self.original_name
            and self.original_name != self.name
            and self.name == self.original_name + "_"
        ):
            # Generate strawberry.field(name='original_name') or strawberry.field(name='original_name', default=value)
            if self.has_default and self.represented_default and self.represented_default != 'None':
                # Use represented_default which is already properly formatted
                return f"strawberry.field(name='{self.original_name}', default={self.represented_default})"
            else:
                return f"strawberry.field(name='{self.original_name}')"
        
        # For non-reserved keyword fields, use the default behavior
        return super().field

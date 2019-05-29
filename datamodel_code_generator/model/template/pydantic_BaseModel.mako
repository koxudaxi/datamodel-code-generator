%for decorator in decorators:
${decorator}
%endfor
class ${class_name}(BaseModel):
% for field in fields:
    % if field.required:
    ${field.name}: ${field.type_hint}
    % else:
    ${field.name}: ${field.type_hint} = ${field.default}
    % endif
% endfor
# This mapping is a workaround for any specific fields which end up being too difficult to map
# Try to include a comment as to each field if you modify this describing why the type should be
# overridden that way code reviewers can examine to see if it's an appropriate use case for this file.

NAME_OVERRIDE_MAPPING = {
    'AppetiteEligibilityAnswer': {
        # subQuestions calls a circular reference possibly infinitely, and schematics doesn't support forward references
        'subQuestions': "ListType(BaseType(), serialized_name='subQuestions')"},
    'PortalUserInputs': {
        # eligibilityAnswers uses `None` as an acceptable field, yet is required. Schematics has a builtin check to not
        # accept None as a value unless required is False
        'eligibilityAnswers': "DictType(BaseType(required=False), serialized_name='eligibilityAnswers')"
    }

}

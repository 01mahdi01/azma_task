# from django.core.exceptions import ValidationError
# import jsonschema
#
#
# class JSONSchemaValidator:
#     def __init__(self, limit_value):
#         self.schema = limit_value
#
#     def __call__(self, value):
#         try:
#             jsonschema.validate(value, self.schema)
#         except jsonschema.exceptions.ValidationError as e:
#             raise ValidationError(
#                 f"Invalid JSON data: {e.message}",
#                 params={'value': value}
#             )


MY_JSON_FIELD_SCHEMA = {
    "type": "object",
    "properties": {
        "command_type": {
            "type": "string",
            "maxLength": 50
        },
        "body": {
            "type": "string",
            # "pattern": r"^\d{3}-\d{3}-\d{4}$"  # Regex to match a phone number format
        },
        "parameters": {
            "type": "array",  # Should be "array" for a list of items
            "items": {
                "type": "string"  # The items in the list should be strings
            }
        }
    },
    "required": ["command_type", "body"],
    "additionalProperties": True
}

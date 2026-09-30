from drf_spectacular.utils import extend_schema

def basic_validation_docs():
    return extend_schema(
        description="API Validate Master Excel File",
        tags = ['basic-validation-distribution'],
    )
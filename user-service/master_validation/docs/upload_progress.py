from drf_spectacular.utils import extend_schema

def upload_progress_docs():
    return extend_schema(
        description="API get master Upload Progress basis in Process ID",
        tags = ['master-validation-docs'],
        responses=
        {
            200:{
                "recordCount": "",
                "data": {
                    "progress":'0',
                    "total_rows":'0'
                },
                "status": 0,
                "msg": "record count",
                "errorCount": None,
                "error": None,
                "conflictErrorCount": None,
                "conflictError": None
                },
            400:{'error': ''}
        },
    )
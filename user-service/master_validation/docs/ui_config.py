from drf_spectacular.utils import extend_schema

def get_uiConfig_docs():
    return extend_schema(
        description="API get master Upload Progress basis in Process ID",
        tags = ['master-validation-docs'],
        responses={
                    200:
                        {
                        "recordCount": "18",
                        "data": [
                                    {
                                        "id": "1",
                                        "name": "SKU",
                                        "fields": [
                                            {
                                                "displayName": "SKUCode",
                                                "key": "sc",
                                                "col_Position": "1",
                                                "visible": True,
                                                "isAdd": True,
                                                "isEdit": False,
                                                "isDownload": True,
                                                "isApplicable": True
                                            },
                                        ]
                                    }
                                ]
                        }
                    }
    )
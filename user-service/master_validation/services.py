"""Define the master validaiton services which will be called in views"""


class DatabaseSyncServices:
    def __init__(self) -> None:
        pass
    def sync_prefinal_table_to_final_table(self,source_model, destination_model):
        source_data = source_model.objects.all()

    # Get the fields dynamically from the SourceModel
        fields = [field.name for field in source_model._meta.get_fields()]

        # Create a list to hold DestinationModel objects
        destination_objects = []

        # Iterate through fetched data and create DestinationModel objects
        for source_obj in source_data:
            destination_obj_kwargs = {}
            for field in fields:
                value = getattr(source_obj, field)
                destination_obj_kwargs[field] = value
            destination_obj = destination_model(**destination_obj_kwargs)
            destination_objects.append(destination_obj)

        # In case it is an add operation Bulk create DestinationModel objects
        destination_model.objects.bulk_create(destination_objects)



    def sync_final_table_to_prefinal_table(self):
        pass
        # logic that will push the data in final table to the pre final table
    
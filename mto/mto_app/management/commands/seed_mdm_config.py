import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from mto_app.models import MDMConfiguration, MasterMapper, TaskActionStatusMaster, TaskActionTypeMaster, CloseTypeMaster

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seeds MasterMapper and MDMConfiguration tables with full sync detection.'

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                self.stdout.write(
                    self.style.SUCCESS('Starting MDM Configuration seeding...')
                )

                if self.check_seeding_status():
                    return

                self.stdout.write(self.style.SUCCESS("Starting seeding process..."))
                
                self.seed_master_mapper()
                self.seed_mdm_configuration()
                self.seed_task_action_status_master()
                self.seed_task_action_type_master()
                self.seed_close_type_master()

                self.stdout.write(self.style.SUCCESS("Seeding process for MDM Configuration completed."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Seeding failed. Rolled back all changes. Error: {str(e)}"))

    def check_seeding_status(self):
        """Check if seeding has already been performed"""
        # Count existing entries
        total = sum([
            MasterMapper.objects.count(),
            MDMConfiguration.objects.count(),
            TaskActionStatusMaster.objects.count(),
            TaskActionTypeMaster.objects.count(),
            CloseTypeMaster.objects.count()
        ])

        if total > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Seeding appears to have been performed already. Found {total} total seeded entries.'
                )
            )
            if not self.confirm_proceed():
                self.stdout.write(self.style.SUCCESS('Seeding cancelled by user.'))
                return True

        return False

    def confirm_proceed(self):
        """Ask user for confirmation to proceed with updates"""
        try:
            response = input('Do you want to proceed anyway? (y/N): ').lower().strip()
            return response in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            return False

    def seed_master_mapper(self):
        """Seed the MasterMapper data - only update when values actually change"""
        logger.info("Seeding MasterMapper...")
        
        created_count = 0
        skipped_count = 0
        
        data = [
            {'master_id': 501, 'master_name': 'Buffer Master', 'display_name': 'Buffer', 'is_valid': True},
            {'master_id': 502, 'master_name': 'CCR Master', 'display_name': 'CCR', 'is_valid': True},
            {'master_id': 503, 'master_name': 'POOGI Reason Master', 'display_name': 'POOGI Reasons', 'is_valid': True},
            {'master_id': 504, 'master_name': 'Calendar', 'display_name': 'Calendar', 'is_valid': True}
        ]

        # FETCH KEYS OF EXISTING RECORDS FOR EFFICIENT LOOKUPS 
        existing_master_ids = set(MasterMapper.objects.values_list('master_id', 'master_name'))
        self.stdout.write(f"  Found {len(existing_master_ids)} existing MasterMapper keys.")

        mappers_to_create = []
        for item in data:
            lookup_key = (item['master_id'] ,item['master_name'])
            # If the master_id already exists in the database, we skip this item.
            if lookup_key in existing_master_ids:
                skipped_count += 1
                continue
            # Entry does not exist, so we prepare it for creation
            mappers_to_create.append(MasterMapper(**item))
                    
        # PERFORM A SINGLE BULK CREATE OPERATION 
        if mappers_to_create:
            # Create all the new records in one database query.
            created_objects = MasterMapper.objects.bulk_create(mappers_to_create)
            created_count = len(created_objects)
            self.stdout.write(f"  Bulk created {created_count} new MasterMappers.")
        else:
            self.stdout.write("  No new MasterMappers to create.")
            
        # SHOW SUMMARY 
        self.stdout.write(
            self.style.SUCCESS(
                f'MasterMapper: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )

    def seed_mdm_configuration(self):
            """Seed the MDMConfiguration data - only update when values actually change"""
            logger.info("Seeding MDMConfiguration...")
            
            created_count = 0
            skipped_count = 0
            
            data = [
                {'display_name': 'Buffer Id', 'col_code': 'bid', 'table_field': 'buffer_id', 'col_position': 1, 'visible': False, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Buffer Id', 'master_mapper_id': 1},
                {'display_name': 'Buffer Code', 'col_code': 'bcd', 'table_field': 'buffer_code', 'col_position': 2, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Buffer Code', 'master_mapper_id': 1},
                {'display_name': 'Buffer Description', 'col_code': 'bd', 'table_field': 'buffer_desc', 'col_position': 3, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Buffer Description', 'master_mapper_id': 1},
                {'display_name': 'Buffer Size', 'col_code': 'bsz', 'table_field': 'buffer_size', 'col_position': 4, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Buffer Size', 'master_mapper_id': 1},
                {'display_name': 'SLT', 'col_code': 'slt', 'table_field': 'SLT', 'col_position': 5, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'SLT', 'master_mapper_id': 1},
                {'display_name': 'MLT', 'col_code': 'mlt', 'table_field': 'MLT', 'col_position': 6, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'MLT', 'master_mapper_id': 1},
                {'display_name': 'Is Blue', 'col_code': 'ib', 'table_field': 'is_blue', 'col_position': 7, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'boolean', 'header': 'Is Blue', 'master_mapper_id': 1},
                {'display_name': 'Buffer Type', 'col_code': 'bt', 'table_field': 'buffer_type_id', 'col_position': 8, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Buffer Type', 'master_mapper_id': 1},
                {'display_name': 'Buffer Type Name', 'col_code': 'btype', 'table_field': 'buffer_type', 'col_position': 9, 'visible': False, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Buffer Type Name', 'master_mapper_id': 1},
                {'display_name': 'Is Active', 'col_code': 'iv', 'table_field': 'is_valid', 'col_position': 10, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'boolean', 'header': 'Is Active', 'master_mapper_id': 1},
                {'display_name': 'CCR Id', 'col_code': 'cid', 'table_field': 'ccr_id', 'col_position': 1, 'visible': False, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'CCR Id', 'master_mapper_id': 2},
                {'display_name': 'CCR Code', 'col_code': 'ccd', 'table_field': 'ccr_code', 'col_position': 2, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'CCR Code', 'master_mapper_id': 2},
                {'display_name': 'CCR Name', 'col_code': 'cnm', 'table_field': 'ccr_name', 'col_position': 3, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'CCR Name', 'master_mapper_id': 2},
                {'display_name': 'Capacity Per Day', 'col_code': 'cpd', 'table_field': 'capacity_per_day', 'col_position': 4, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Capacity Per Day', 'master_mapper_id': 2},
                {'display_name': 'Working Hrs Per Day', 'col_code': 'whpd', 'table_field': 'working_hours_per_day', 'col_position': 5, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Working Hrs Per Day', 'master_mapper_id': 2},
                {'display_name': 'Scheduling Horizon', 'col_code': 'sh', 'table_field': 'schedule_horizon', 'col_position': 6, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Scheduling Horizon', 'master_mapper_id': 2},
                {'display_name': 'FOL Horizon', 'col_code': 'fh', 'table_field': 'fol_horizon', 'col_position': 7, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'FOL Horizon', 'master_mapper_id': 2},
                {'display_name': 'Residual Buffer', 'col_code': 'rb', 'table_field': 'residual_buffer', 'col_position': 8, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Residual Buffer', 'master_mapper_id': 2},
                {'display_name': 'Plant', 'col_code': 'pl', 'table_field': 'plant', 'col_position': 9, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Plant', 'master_mapper_id': 2},
                {'display_name': 'Department', 'col_code': 'dp', 'table_field': 'dept', 'col_position': 10, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Department', 'master_mapper_id': 2},
                {'display_name': 'Cumulative WIP Limit', 'col_code': 'cwl', 'table_field': 'cumulative_wip_limit', 'col_position': 11, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Cumulative WIP Limit', 'master_mapper_id': 2},
                {'display_name': 'Attribute 1', 'col_code': 'a1', 'table_field': 'ccr_attr1', 'col_position': 12, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Attribute 1', 'master_mapper_id': 2},
                {'display_name': 'Attribute 2', 'col_code': 'a2', 'table_field': 'ccr_attr2', 'col_position': 13, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Attribute 2', 'master_mapper_id': 2},
                {'display_name': 'Attribute 3', 'col_code': 'a3', 'table_field': 'ccr_attr3', 'col_position': 14, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Attribute 3', 'master_mapper_id': 2},
                {'display_name': 'Attribute 4', 'col_code': 'a4', 'table_field': 'ccr_attr4', 'col_position': 15, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Attribute 4', 'master_mapper_id': 2},
                {'display_name': 'Attribute 5', 'col_code': 'a5', 'table_field': 'ccr_attr5', 'col_position': 16, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Attribute 5', 'master_mapper_id': 2},
                {'display_name': 'Attribute 6', 'col_code': 'a6', 'table_field': 'ccr_attr6', 'col_position': 17, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Attribute 6', 'master_mapper_id': 2},
                {'display_name': 'Attribute 7', 'col_code': 'a7', 'table_field': 'ccr_attr7', 'col_position': 18, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Attribute 7', 'master_mapper_id': 2},
                {'display_name': 'Attribute 8', 'col_code': 'a8', 'table_field': 'ccr_attr8', 'col_position': 19, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Attribute 8', 'master_mapper_id': 2},
                {'display_name': 'Attribute 9', 'col_code': 'a9', 'table_field': 'ccr_attr9', 'col_position': 20, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Attribute 9', 'master_mapper_id': 2},
                {'display_name': 'Attribute 10', 'col_code': 'a10', 'table_field': 'ccr_attr10', 'col_position': 21, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Attribute 10', 'master_mapper_id': 2},
                {'display_name': 'CCR Group', 'col_code': 'cgid', 'table_field': 'ccr_group', 'col_position': 22, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'CCR Group', 'master_mapper_id': 2},
                {'display_name': 'Major Reason Id', 'col_code': 'majId', 'table_field': 'major_reason_id', 'col_position': 1, 'visible': False, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Major Reason Id', 'master_mapper_id': 3},
                {'display_name': 'Major Reason Code', 'col_code': 'majcd', 'table_field': 'major_reason_code', 'col_position': 2, 'visible': False, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Major Reason Code', 'master_mapper_id': 3},
                {'display_name': 'Major Reason Description', 'col_code': 'majdsc', 'table_field': 'major_reason_desc', 'col_position': 3, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Major Reason Description', 'master_mapper_id': 3},
                {'display_name': 'Minor Reason Id', 'col_code': 'minId', 'table_field': 'minor_reason_id', 'col_position': 4, 'visible': False, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Minor Reason Id', 'master_mapper_id': 3},
                {'display_name': 'Minor Reason Code', 'col_code': 'mincd', 'table_field': 'minor_reason_code', 'col_position': 5, 'visible': False, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Minor Reason Code', 'master_mapper_id': 3},
                {'display_name': 'Minor Reason Description', 'col_code': 'mindsc', 'table_field': 'minor_reason_desc', 'col_position': 6, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Minor Reason Description', 'master_mapper_id': 3},
                {'display_name': 'Plant', 'col_code': 'pl', 'table_field': 'plant_id', 'col_position': 7, 'visible': False, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Plant', 'master_mapper_id': 3},
                {'display_name': 'Plant Name', 'col_code': 'plnm', 'table_field': 'plant_name', 'col_position': 8, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Plant Name', 'master_mapper_id': 3},
                {'display_name': 'Holiday Id', 'col_code': 'hid', 'table_field': 'id', 'col_position': 1, 'visible': False, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Holiday Id', 'master_mapper_id': 4},
                {'display_name': 'Day Of Week', 'col_code': 'dow', 'table_field': 'day_of_week', 'col_position': 2, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Day Of Week', 'master_mapper_id': 4},
                {'display_name': 'Start Date', 'col_code': 'sd', 'table_field': 'holiday_start_date', 'col_position': 3, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Start Date', 'master_mapper_id': 4},
                {'display_name': 'End Date', 'col_code': 'ed', 'table_field': 'holiday_end_date', 'col_position': 4, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'End Date', 'master_mapper_id': 4},
                {'display_name': 'Is Working Day', 'col_code': 'iwd', 'table_field': 'is_working_day', 'col_position': 5, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Is Working Day', 'master_mapper_id': 4},
                {'display_name': 'Description', 'col_code': 'dsc', 'table_field': 'description', 'col_position': 6, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Description', 'master_mapper_id': 4},
                {'display_name': 'CCR', 'col_code': 'ccr_id', 'table_field': 'ccr', 'col_position': 7, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'CCR', 'master_mapper_id': 4},
                {'display_name': 'Plant', 'col_code': 'plid', 'table_field': 'plant', 'col_position': 8, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Plant', 'master_mapper_id': 4},
                {'display_name': 'Plant Name', 'col_code': 'plnm', 'table_field': 'plant__plant_name', 'col_position': 9, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Plant Name', 'master_mapper_id': 4},
                {'display_name': 'Repeatation Bucket', 'col_code': 'rb', 'table_field': 'repeatation_bucket', 'col_position': 10, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'string', 'header': 'Repeatation Bucket', 'master_mapper_id': 4},
                {'display_name': 'Repeat Duration in Weeks', 'col_code': 'rd', 'table_field': 'repeat_duration_in_weeks', 'col_position': 11, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'number', 'header': 'Repeat Duration in Weeks', 'master_mapper_id': 4},
                {'display_name': 'Is Active', 'col_code': 'iv', 'table_field': 'is_valid', 'col_position': 23, 'visible': True, 'cell_alignment': 'center', 'is_valid': True, 'data_type': 'boolean', 'header': 'Is Active', 'master_mapper_id': 2},
            ]

            # FETCH DATA FOR EFFICIENT LOOKUPS            
            # Fetch all MasterMapper objects to resolve the foreign key relationship.
            master_mappers_map = {mapper.id: mapper for mapper in MasterMapper.objects.all()}
            self.stdout.write(f"  Fetched {len(master_mappers_map)} MasterMappers.")
            
            # Fetch the composite keys of all existing configs
            existing_config_keys = set(
                MDMConfiguration.objects.values_list('master_mapper_id', 'col_code')
            )
            self.stdout.write(f"  Found {len(existing_config_keys)} existing MDMConfiguration keys.")
            
            configs_to_create = []
            for item in data:
                lookup_key = (item['master_mapper_id'], item['col_code'])
                
                # If the key already exists in the database, we skip this item.
                if lookup_key in existing_config_keys:
                    skipped_count += 1
                    continue
            
                # Entry does not exist, prepare it for creation       
                master_mapper_obj = master_mappers_map.get(item['master_mapper_id'])
                
                # If the related MasterMapper doesn't exist, we can't create this config.
                if not master_mapper_obj:
                    self.stdout.write(self.style.WARNING(
                        f"  Skipping config with col_code='{item['col_code']}' because "
                        f"MasterMapper with id={item['master_mapper_id']} was not found."
                    ))
                    continue
                # Create a new model instance (but DON'T save it to the DB yet).
                configs_to_create.append(
                    MDMConfiguration(
                        master_mapper=master_mapper_obj,
                        display_name=item['display_name'],
                        col_code=item['col_code'],
                        table_field=item['table_field'],
                        col_position=item['col_position'],
                        visible=item['visible'],
                        cell_alignment=item['cell_alignment'],
                        is_valid=item['is_valid'],
                        data_type=item['data_type'],
                        header=item['header']
                    )
                )

            # PERFORM A SINGLE BULK CREATE OPERATION
            if configs_to_create:
                # Create all the new records in one database query.
                created_objects = MDMConfiguration.objects.bulk_create(configs_to_create)
                created_count = len(created_objects)
                self.stdout.write(f"  Bulk created {created_count} new MDMConfigurations.")
            else:
                self.stdout.write("  No new MDMConfigurations to create.")            

            # SHOW SUMMARY
            self.stdout.write(
                self.style.SUCCESS(
                    f'MDMConfiguration: {created_count} created, {skipped_count} skipped.'
                )
            )     
            
    def seed_task_action_status_master(self):
        """Seed the TaskActionStatusMaster table - only update when values actually change"""
        logger.info("Seeding TaskActionStatusMaster...")

        created_count = 0
        skipped_count = 0

        data = [
            {'task_status_id': 1, 'task_status_desc': 'Pending'},
            {'task_status_id': 2, 'task_status_desc': 'Partially Approved'},
            {'task_status_id': 3, 'task_status_desc': 'Approved'},
            {'task_status_id': 4, 'task_status_desc': 'Rejected'},
        ]

        # FETCH KEYS OF EXISTING RECORDS 
        existing_ids = set(TaskActionStatusMaster.objects.values_list('task_status_id', 'task_status_desc'))
        self.stdout.write(f"  Found {len(existing_ids)} existing TaskActionStatusMaster keys.")

        #  PREPARE NEW RECORDS IN-MEMORY 
        status_to_create = []

        for item in data:
            lookup_key = (item['task_status_id'], item['task_status_desc'])
            if lookup_key in existing_ids:
                skipped_count += 1
                continue
            
            status_to_create.append(TaskActionStatusMaster(**item))

        # PERFORM A SINGLE BULK CREATE OPERATION 
        created_count = 0
        if status_to_create:
            created_objects = TaskActionStatusMaster.objects.bulk_create(status_to_create)
            created_count = len(created_objects)
            self.stdout.write(f"  Bulk created {created_count} new TaskActionStatusMaster records.")
        else:
            self.stdout.write("  No new TaskActionStatusMaster records to create.")

        # SHOW SUMMARY 
        self.stdout.write(
            self.style.SUCCESS(
                f'TaskActionStatusMaster: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )

    def seed_task_action_type_master(self):
        """Seed the TaskActionTypeMaster table - only update when values actually change"""
        logger.info("Seeding TaskActionTypeMaster...")

        created_count = 0
        skipped_count = 0

        data = [
            {'action_type_id': 1, 'action_type_desc': 'Add'},
            {'action_type_id': 2, 'action_type_desc': 'Modify'},
            {'action_type_id': 3, 'action_type_desc': 'Delete'},
        ]
        
        # FETCH KEYS OF EXISTING RECORDS 
        existing_ids = set(TaskActionTypeMaster.objects.values_list('action_type_id', 'action_type_desc'))
        self.stdout.write(f"  Found {len(existing_ids)} existing TaskActionTypeMaster keys.")

        # PREPARE NEW RECORDS IN-MEMORY 
        types_to_create = []

        for item in data:
            lookup_key = (item['action_type_id'], item['action_type_desc'])
            if lookup_key in existing_ids:
                skipped_count += 1
                continue
            
            types_to_create.append(TaskActionTypeMaster(**item))

        # PERFORM A SINGLE BULK CREATE OPERATION
        if types_to_create:
            created_objects = TaskActionTypeMaster.objects.bulk_create(types_to_create)
            created_count = len(created_objects)
            self.stdout.write(f"  Bulk created {created_count} new TaskActionTypeMaster records.")
        else:
            self.stdout.write("  No new TaskActionTypeMaster records to create.")

        # SHOW SUMMARY
        self.stdout.write(
            self.style.SUCCESS(
                f'TaskActionTypeMaster: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )

    def seed_close_type_master(self):
        """Seed the CloseTypeMaster table - only update when values actually change"""
        logger.info("Seeding CloseTypeMaster...")

        data = [
            {"close_type": "Short Close", "close_type_code": "0", "is_valid": True},
            {"close_type": "Complete Close", "close_type_code": "1", "is_valid": True},
        ]

        created_count = 0
        skipped_count = 0

        # FETCH KEYS OF EXISTING RECORDS
        existing_types = set(CloseTypeMaster.objects.values_list('close_type', flat=True))
        self.stdout.write(f"  Found {len(existing_types)} existing CloseTypeMaster keys.")

        # PREPARE NEW RECORDS IN-MEMORY 
        close_types_to_create = []

        for item in data:
            if item['close_type'] in existing_types:
                skipped_count += 1
                continue
            
            close_types_to_create.append(CloseTypeMaster(**item))

        # PERFORM A SINGLE BULK CREATE OPERATION
        created_count = 0
        if close_types_to_create:
            created_objects = CloseTypeMaster.objects.bulk_create(close_types_to_create)
            created_count = len(created_objects)
            self.stdout.write(f"  Bulk created {created_count} new CloseTypeMaster records.")
        else:
            self.stdout.write("  No new CloseTypeMaster records to create.")

        # SHOW SUMMARY
        self.stdout.write(
            self.style.SUCCESS(
                f'CloseTypeMaster: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )

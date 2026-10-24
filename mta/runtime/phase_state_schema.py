"""Two finite calculation consumers absent from the native row catalogue."""

TABLES = {
    'phase/PickBand': [(name, 'nvarchar') for name in
        ('sku_code', 'location_code', 'parent_location_code',
         'to_black', 'to_red', 'to_yellow', 'to_green', 'to_blue')],
    'phase/AdvanceStock': [('sku_code', 'nvarchar'), ('source_location_code', 'nvarchar'),
                           ('allocated_quantity', 'bigint')],
}

class APIVariable:
    allowed_chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789@_!#$%^&*()<>?/|}{~:"
    allowed_username_chars = r'^[a-zA-Z0-9_]+$'
    special_characters = r"!@#$%^&*()-_=+[]{};:,.<>?/|\\~`"
    allowed_username_chars_error = "[a-zA-Z0-9_]"
    id = "id"
    product_hierarchy_1 = "product_hierarchy_1"
    product_hierarchy_2 = "product_hierarchy_2"
    product_hierarchy_3 = "product_hierarchy_3"
    wh_type = "wh_type"
    wh_location_group = "wh_location_group"
    wh_region = "wh_region"
    product_columns = ["product_hierarchy_1", "product_hierarchy_2", "product_hierarchy_3"]
    location_columns = ["wh_region", "wh_type", "wh_location_group"]

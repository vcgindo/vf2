from django.db.models import Q

numerical_cols = { 
'norm', 'norm_min', 'norm_max', 'rlt', 'mvd', 'nhd', 'pack_size', 'rosn_active', 'rosn_seasonality_active', 
'returns_pm_on_released_capital', 'discount_eoss', 'cogs_mrp', 'cost_of_capital_pa', 'shipment_cost_per_pc', 'min_rosn', 'incr_rosn', 
'capacity_pcs', 'capacity_sets',
'priority', 
'mpsad','mdq',
'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
'variant', 
'price', 
}

boolean_cols = {'movement_status'}


def create_dynamic_filter_query(filter_list):

    boolean_filter_variation_for_true = ['True', 'true', 'TRUE']
    boolean_filter_variation_for_false = ['False', 'false', 'FALSE']

    q_objects = Q()
    
    for filter_dict in filter_list:
        # Determine the lookup expression
        lookup_expr = filter_dict['attributeName']
        lookup_value = filter_dict['value']


        if filter_dict['op'] == '=':
            if (lookup_expr in boolean_cols) and (lookup_value in boolean_filter_variation_for_true):
                lookup_value = True
            elif (lookup_expr in boolean_cols) and (lookup_value in boolean_filter_variation_for_false):
                lookup_value = False
            elif (lookup_expr in boolean_cols):
                return Q(**{lookup_expr: True}) & Q(**{lookup_expr: False})
            q_objects &= Q(**{lookup_expr: lookup_value})
        elif filter_dict['op'] == '!=':
            if (lookup_expr in numerical_cols) and (lookup_value.isdigit()):
                q_objects &= ~Q(**{f'{lookup_expr}__exact': lookup_value})
            elif (lookup_expr in numerical_cols) and (not lookup_value.isdigit()): 
                return Q(**{lookup_expr:-9999999})
            else:
                return Q(**{lookup_expr:[]})
        elif filter_dict['op'] == '>':
            if (lookup_expr in numerical_cols) and (lookup_value.isdigit()):
                q_objects &= Q(**{f'{lookup_expr}__gt': f'{lookup_value}'})
            elif (lookup_expr in numerical_cols) and (not lookup_value.isdigit()): 
                return Q(**{lookup_expr:-9999999})
            else:
                return Q(**{lookup_expr:[]})
        elif filter_dict['op'] == '>=':
            if (lookup_expr in numerical_cols) and (lookup_value.isdigit()):
                q_objects &= Q(**{f'{lookup_expr}__gte': f'{lookup_value}'})
            elif (lookup_expr in numerical_cols) and (not lookup_value.isdigit()): 
                return Q(**{lookup_expr:-9999999})
            else:
                return Q(**{lookup_expr:[]})
        elif filter_dict['op'] == '<':
            if (lookup_expr in numerical_cols) and (lookup_value.isdigit()):
                q_objects &= Q(**{f'{lookup_expr}__lt': f'{lookup_value}'})
            elif (lookup_expr in numerical_cols) and (not lookup_value.isdigit()): 
                return Q(**{lookup_expr:-9999999})
            else:
                return Q(**{lookup_expr:[]})
        elif filter_dict['op'] == '<=':
            if (lookup_expr in numerical_cols) and (lookup_value.isdigit()):
                q_objects &= Q(**{f'{lookup_expr}__lte': f'{lookup_value}'})
            elif (lookup_expr in numerical_cols) and (not lookup_value.isdigit()): 
                return Q(**{lookup_expr:-9999999})
            else:
                return Q(**{lookup_expr:[]})
        elif filter_dict['op'] == 'contains':
            if (not lookup_expr in numerical_cols) and (not lookup_expr in boolean_cols):
                q_objects &= Q(**{f'{lookup_expr}__contains': lookup_value})
            elif (not lookup_expr in numerical_cols) and (lookup_expr in boolean_cols):
                return Q(**{lookup_expr: True}) & Q(**{lookup_expr: False})
            else:
                return Q(**{lookup_expr:-9999999})
        elif filter_dict['op'] == 'startsWith':
            if (not lookup_expr in numerical_cols) and (not lookup_expr in boolean_cols):
                q_objects &= Q(**{f'{lookup_expr}__startswith': lookup_value})
            elif (not lookup_expr in numerical_cols) and (lookup_expr in boolean_cols):
                return Q(**{lookup_expr: True}) & Q(**{lookup_expr: False})
            else:
                return Q(**{lookup_expr:-9999999})
        elif filter_dict['op'] == 'endsWith':
            if (not lookup_expr in numerical_cols) and (not lookup_expr in boolean_cols):
                q_objects &= Q(**{f'{lookup_expr}__endswith': lookup_value})    
            elif (not lookup_expr in numerical_cols) and (lookup_expr in boolean_cols):
                return Q(**{lookup_expr: True}) & Q(**{lookup_expr: False})
            else:
                return Q(**{lookup_expr:-9999999})
        elif filter_dict['op'] == 'hasValue':
            if lookup_value in boolean_filter_variation_for_true:
                lookup_value = True
                q_objects &= Q(**{lookup_expr: lookup_value})
            elif lookup_value in boolean_filter_variation_for_false:
                lookup_value = False
                q_objects &= Q(**{lookup_expr: lookup_value})
            else: 
                q_objects &= Q(**{f'{lookup_expr}__exact': lookup_value})
        elif filter_dict['op'] == 'hasNoValue':
            if (not lookup_expr in numerical_cols) and (not lookup_expr in boolean_cols):
                q_objects &= ~Q(**{f'{lookup_expr}__exact': lookup_value})
            elif (not lookup_expr in numerical_cols) and (lookup_expr in boolean_cols):
                return Q(**{lookup_expr: True}) & Q(**{lookup_expr: False})
            else:
                return Q(**{lookup_expr:-9999999})

    return q_objects
 

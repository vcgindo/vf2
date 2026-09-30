from django.db.models import Q
def get_query_builder(df):
    query = Q()
    for _, row in df.iterrows():
        q_obj = Q(
            ph1 = row['wh_region'],
            ph2 = row['wh_type'],
            ph3 = row['wh_location_group'], 
        )
        query &= q_obj  # Use | (OR) to combine Q objects

    return query
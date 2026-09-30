from ..models.prefinal_models import *
from ..models.final_models import *
from apps_forced_closure.models.contact import ContactDetail
from api.models import SkuLocDeploymentMaster, LocationsFilter, LocationMasterModels, LocationPriorityMasterModel, \
    PivotalSizeMasterModels, ProductFilter, SeasonatilyMaster, SKUMasterModels


MASTER_ID_TO_PREFINAL_MODEL_MAPPING = {
    "15":ContactDetail,
    "16":PreFinalSkuLocDeploymentMasterModel,
    "17":PreFinalDiscountPeriodMasterModel,
    "18":PreFinalISTYieldMasterModel,
    "19":PreFinalLocationPermissionMasterModel,
    "20":PreFinalLocationCapacityMasterModel,
    "21":PreFinalLocationMasterModel,
    "23":PreFinalLocationPriorityMasterModel,
    "24":PreFinalPivotalSizeMasterModel,
    "25":PreFinalProductPermissionMasterModel,
    "26":PreFinalSeasonalityMasterModel,
    "27":PreFinalSKUMasterModel,
}

MASTER_ID_TO_FINAL_MODEL_MAPPING = {
    "15":ContactDetail,
    "16":SkuLocDeploymentMaster,
    "17":DiscountPeriodMasterModel,
    "18":ISTYieldMasterModel,
    "19":LocationsFilter,
    "20":LocationCapacityMasterModel,
    "21":LocationMasterModels,
    "23":LocationPriorityMasterModel,
    "24":PivotalSizeMasterModels,
    "25":ProductFilter,
    "26":SeasonatilyMaster,
    "27":SKUMasterModels,
}


PREFINAL_TO_FINAL_DB_MAPPING = {
    PreFinalContactDetailMasterModel: FinalContactDetailMasterModel,
    PreFinalSkuLocDeploymentMasterModel: FinalSkuLocDeploymentMasterModel,
    PreFinalDiscountPeriodMasterModel: DiscountPeriodMasterModel,
    PreFinalISTYieldMasterModel: ISTYieldMasterModel,
    PreFinalLocationPermissionMasterModel: FinalLocationsPermissionMasterModel,
    PreFinalLocationCapacityMasterModel: LocationCapacityMasterModel,
    PreFinalLocationMasterModel: FinalLocationMasterModel,
    PreFinalLocationPriorityMasterModel: FinalLocationPriorityMasterModel,
    PreFinalPivotalSizeMasterModel: FinalPivotalSizeMasterModel,
    PreFinalProductPermissionMasterModel:FinalProductPermissionMasterModel,
    PreFinalSeasonalityMasterModel: FinalSeasonatilyMasterModel,
    PreFinalSKUMasterModel: FinalSKUMasterModel
}


PRE_FINAL_TABLE_TO_TABLE_KEY_MAPPER = {
    ContactDetail:['wh_code'],
    SkuLocDeploymentMaster:['sku_code','wh_code'],
    DiscountPeriodMasterModel:['launch_period'],
    ISTYieldMasterModel:['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'],
    LocationsFilter:['wh_region'],
    LocationCapacityMasterModel:['wh_code','product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'],
    LocationMasterModels:['wh_code'],
    LocationPriorityMasterModel:['product_hierarchy_1','wh_code'],
    PivotalSizeMasterModels:['wh_code','product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'],
    ProductFilter:None,
    SeasonatilyMaster:['wh_code','product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'],
    SKUMasterModels:['sku_code']
    
}
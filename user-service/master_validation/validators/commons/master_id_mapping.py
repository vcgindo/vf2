from ...schemas.SKULocation import SKULocationValidations
from ...schemas.Location import LocationValidations
from ...schemas.SKU import SKUValidations
from ...schemas.SOB import SOBValidations
from ...schemas.MOQ import MOQValidations
from ...schemas.StopPIPO import StopPIPOValidations
from ...schemas.AddPO import AddPOValidations
from ...schemas.AddPIPO import AddPIPOValidations
from ...schemas.AddTargetNorm import AddTargetNormValidations
from ...schemas.SeasonalityStatus import SeasonalityStatusValidations
from ...schemas.AbsoluteValueSeasonality import AbsoluteValueSeasonalityValidations
from ...schemas.DeltaPercentageSeasonalitySchema import DeltaPercentageSeasonalityValidations
from ...schemas.ForceNormChange import ForceNormChangeValidations
from .data_types import SKU_LOCATION_DTYPE,SKU_DTYPE,LOCATION_DTYPE,SOB_DTYPE,MOQ_DTYPE,STOP_PIPO_DTYPE,ADD_PO_DTYPE,ADD_PIPO_DTYPE,ADD_TARGET_NORM_DTYPE,SEASONALITY_STATUS_DTYPE,ABSOLUTE_VALUE_SEASONALITY_DTYPE,DELTA_PERCENTAGE_SEASONALITY_DTYPE,FORCE_NORM_CHANGE_DTYPE

MASTER_ID_TO_VALIDATION = {
    '1':SKUValidations,
    '2':LocationValidations,
    '3':SKULocationValidations,
    '4':SOBValidations,
    '5':MOQValidations,
    '6':StopPIPOValidations,
    '7':AddPOValidations,
    '8':AddPIPOValidations,
    '9':AddTargetNormValidations,
    '10':SeasonalityStatusValidations,
    '11':AbsoluteValueSeasonalityValidations,
    '12':DeltaPercentageSeasonalityValidations,
    '13':ForceNormChangeValidations

}

MASTER_ID_TO_DTYPE = {
    '1':SKU_DTYPE,
    '2':LOCATION_DTYPE,
    '3':SKU_LOCATION_DTYPE,
    '4':SOB_DTYPE,
    '5':MOQ_DTYPE,
    '6':STOP_PIPO_DTYPE,
    '7':ADD_PO_DTYPE,
    '8':ADD_PIPO_DTYPE,
    '9':ADD_TARGET_NORM_DTYPE,
    '10':SEASONALITY_STATUS_DTYPE,
    '11':ABSOLUTE_VALUE_SEASONALITY_DTYPE,
    '12':DELTA_PERCENTAGE_SEASONALITY_DTYPE,
    '13':FORCE_NORM_CHANGE_DTYPE

}
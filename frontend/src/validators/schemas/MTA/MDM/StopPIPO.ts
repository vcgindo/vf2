import Joi from "joi";
import { commonValidator, generateCommonMessages,defaultJOIOptions,MAX_CODE_LENGTH,MAX_NAME_LENGTH} from "../../../commons";

export const StopPIPOSchema = Joi.object({
    sc:Joi.string().empty().invalid(null).max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('PhaseOutSKU')),
    posn:Joi.string().empty().max(MAX_NAME_LENGTH).invalid(null),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('LocationCode')),
    ln:Joi.string().empty().max(MAX_NAME_LENGTH),
    onm:Joi.number().integer(),
    cn:Joi.number().integer(),
    nc:Joi.string(),
    pd:Joi.string(),
    pis:Joi.string().empty().invalid(null).max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('PhaseInSkuCode')),
    pisn:Joi.string(),
    pcn:Joi.number().integer(),
    ptn:Joi.number().integer(),
    

}).preferences(defaultJOIOptions)

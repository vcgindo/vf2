import Joi from "joi";
import { commonValidator, generateCommonMessages,defaultJOIOptions,MAX_CODE_LENGTH,MAX_INT_VAL} from "../../../commons";

export const AddTargetNormSchema = Joi.object({
    sc:Joi.string().empty().invalid(null).max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('PhaseInSKUCode')),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('LocationCode')),
    tn:Joi.number().integer().messages({'number.unsafe':`"tn" should be less than ${MAX_INT_VAL}`}),
    
}).preferences(defaultJOIOptions)
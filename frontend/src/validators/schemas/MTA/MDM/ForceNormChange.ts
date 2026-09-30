import Joi from "joi";
import { commonValidator, generateCommonMessages,defaultJOIOptions,MAX_CODE_LENGTH,MAX_INT_VAL} from "../../../commons";

export const ForceNormChangeSchema = Joi.object({
    sc:Joi.string().empty().invalid(null).max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('SKUCode')),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('WhCode')),
    nn:Joi.number().integer().min(0).messages({'number.unsafe':`"nn" should be less than ${MAX_INT_VAL}`}),

}).preferences(defaultJOIOptions)
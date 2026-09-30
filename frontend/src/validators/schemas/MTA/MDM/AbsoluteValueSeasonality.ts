import Joi from "joi";
import { commonValidator, generateCommonMessages,defaultJOIOptions,MAX_CODE_LENGTH,MAX_INT_VAL} from "../../../commons";

export const AbsoluteValueSeasonalitySchema = Joi.object({
    sc:Joi.string().empty().invalid(null).max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('SKUCode')),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('WhCode')),
    sd:Joi.string(),
    ed:Joi.string(),
    tn:Joi.number().integer().messages({'number.unsafe':`TargeNorm should be less than ${MAX_INT_VAL}`}),
    bd:Joi.number().allow(null)

}).preferences(defaultJOIOptions)
import Joi from "joi";
import { commonValidator, generateCommonMessages,defaultJOIOptions,MAX_CODE_LENGTH, MAX_INT_VAL} from "../../../commons";

export const DeltaPercentageSeasonalitySchema = Joi.object({
    sc:Joi.string().empty().invalid(null).max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('SKUCode')),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('WhCode')),
    sd:Joi.string(),
    ed:Joi.string(),
    dnp:Joi.number().integer().min(-100).max(100).messages({'number.unsafe':`"dnp" should be within -100 to 100`}),
    ulc:Joi.number().integer().min(0).messages({'number.unsafe':`"ulc" should be less than ${MAX_INT_VAL}`}),
    bd:Joi.number().integer().min(0).messages({'number.unsafe':`"bd" should be less than ${MAX_INT_VAL}`}),

}).preferences(defaultJOIOptions)
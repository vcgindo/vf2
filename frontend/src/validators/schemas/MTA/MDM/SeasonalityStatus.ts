import Joi from "joi";
import { commonValidator, generateCommonMessages,defaultJOIOptions,MAX_CODE_LENGTH,MAX_NAME_LENGTH,MAX_INT_VAL} from "../../../commons";

const MIN_RLT_VALUE = 3;

const RLTValidator = (value:any,helper:any)=>{
    if (value < MIN_RLT_VALUE) {
        return helper.warn('any.rlt');
    }
    return value;
}

const SeasonalityStatusMessages = {
    "any.rlt":"RLT value should be greater than or equal to " + MIN_RLT_VALUE,
    "number.unsafe":`RLT should be less than ${MAX_INT_VAL}`
}


export const SeasonalityStatusSchema = Joi.object({
    sc:Joi.string().empty().invalid(null).max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('SKUCode')),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('WhCode')),
    wd:Joi.string().empty().max(MAX_NAME_LENGTH),
    sd:Joi.string(),
    ed:Joi.string(),
    tn:Joi.number().integer().messages({'number.unsafe':`TargeNorm should be less than ${MAX_INT_VAL}`}),
    rlt:Joi.number().integer().custom(RLTValidator).messages(SeasonalityStatusMessages),
    dnp:Joi.number().integer().min(0).max(100).messages({'number.unsafe':`DeltaNormPercentage should be less than ${MAX_INT_VAL}`}),
    nn:Joi.number().integer().messages({'number.unsafe':`DeltaNormPercentage should be less than ${MAX_INT_VAL}`}),
    onm:Joi.number().integer().messages({'number.unsafe':`DeltaNormPercentage should be less than ${MAX_INT_VAL}`}),
    ulc:Joi.number().integer().messages({'number.unsafe':`DeltaNormPercentage should be less than ${MAX_INT_VAL}`}),
    bd:Joi.number().integer().messages({'number.unsafe':`DeltaNormPercentage should be less than ${MAX_INT_VAL}`}),
    tp:Joi.string(),
    sts:Joi.string(),
    cmt:Joi.string(),
    skd:Joi.string().empty().max(MAX_NAME_LENGTH)
}).preferences(defaultJOIOptions)



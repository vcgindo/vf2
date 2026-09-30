import Joi from "joi";
import { commonValidator, generateCommonMessages,defaultJOIOptions,MAX_CODE_LENGTH,MAX_INT_VAL,commonValidatorWithSeperator} from "../../../commons";

const SuppCodeValidator = (value:any,helper:any)=>{

    if(helper.prefs.context.WhCode === value) throw new Error('Supplier code and Location code are same');
    return commonValidatorWithSeperator(value,helper);

}

export const MOQSchema = Joi.object({
    sc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('SKUCode')),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).messages(generateCommonMessages('wc')),
    spc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(SuppCodeValidator).required().messages(generateCommonMessages('spc')),
    mq:Joi.number().integer().min(0).messages({'number.unsafe':`"mq" should be less than ${MAX_INT_VAL}`}),

}).preferences(defaultJOIOptions)

export const MOQSchemaDelete = Joi.object({
    sc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('SKUCode')),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('WhCode')),
    spc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(SuppCodeValidator).required().messages(generateCommonMessages('spc')),
}).preferences(defaultJOIOptions)

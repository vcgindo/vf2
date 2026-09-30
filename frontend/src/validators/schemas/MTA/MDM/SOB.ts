import Joi from "joi";
import { commonValidator, generateCommonMessages,defaultJOIOptions,MAX_CODE_LENGTH,commonValidatorWithSeperator} from "../../../commons";

const SuppCodeValidator = (value:any,helper:any)=>{

    if(helper.prefs.context.WhCode === value) throw new Error('Supplier code and Location code are same.');
    return commonValidatorWithSeperator(value,helper);

}

export const SOBSchema = Joi.object({
    sc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('SKUCode')),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('WhCode')),
    // spc:Joi.custom(SuppCodeValidator).required().messages(generateCommonMessages('SupplierCode')),
    spc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(SuppCodeValidator).required().messages(generateCommonMessages('spc')),
    sb:Joi.number().integer().min(0).max(100).messages({'number.unsafe':`"sb" should be within 0 to 100`,'number.min':`"sb" should be within 0 to 100`,'number.max':`"sb" should be within 0 to 100`,}),

}).preferences(defaultJOIOptions)

export const SOBSchemaDelete = Joi.object({
    sc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('SKUCode')),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('WhCode')),
    sb:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator)
}).preferences(defaultJOIOptions)

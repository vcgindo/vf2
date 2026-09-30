import Joi from "joi";
import { commonValidator, generateCommonMessages,defaultJOIOptions,MAX_CODE_LENGTH,MIN_DECIMAL_VAL,MAX_INT_VAL,MAX_NAME_LENGTH,MAX_DECIMAL_VAL,CommonSchema, commonValidatorWithSeperator, DescriptorValidator} from "../../../commons";

export const SKUSchema = Joi.object({
    sc:Joi.string().empty().invalid(null).max(MAX_CODE_LENGTH).custom(commonValidatorWithSeperator).required().messages(generateCommonMessages('sc')),
    sd: Joi.string().empty().max(MAX_NAME_LENGTH).custom(DescriptorValidator).required().messages({...generateCommonMessages("sd"),"string.max": `"sd" should be less than or equal to 125 characters`}),
    ec:Joi.number().integer().empty().greater(MIN_DECIMAL_VAL).max(MAX_INT_VAL).messages({'number.unsafe':`"ec" should be less than ${MAX_DECIMAL_VAL}`}),
    wt:Joi.number().empty().allow(null,'').greater(MIN_DECIMAL_VAL).max(MAX_DECIMAL_VAL).messages({'number.unsafe':`"wt" should be less than ${MAX_DECIMAL_VAL}`}),
    vm:Joi.number().empty().allow(null,'').greater(MIN_DECIMAL_VAL).max(MAX_DECIMAL_VAL).messages({'number.unsafe':`"vm" should be less than ${MAX_DECIMAL_VAL}`}),
    ...CommonSchema

}).preferences(defaultJOIOptions)

export const SKUSchemaDelete = Joi.object({
    sc:Joi.string().empty().invalid(null).max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('SKUCode'))
}).preferences(defaultJOIOptions)

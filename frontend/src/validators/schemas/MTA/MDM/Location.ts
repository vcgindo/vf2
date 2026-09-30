import Joi from "joi";
import { commonValidator, generateCommonMessages,defaultJOIOptions,MAX_CODE_LENGTH,MAX_NAME_LENGTH,CommonSchema,commonValidatorWithSeperator, DescriptorValidator} from "../../../commons";

export const LocationSchema = Joi.object({
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidatorWithSeperator).required().messages(generateCommonMessages('WhCode')),
    wd:Joi.string().empty().max(MAX_NAME_LENGTH).custom(DescriptorValidator).required().messages({...generateCommonMessages("sd"),"string.max": `"wd" should be less than or equal to 125 characters`}),
    l:Joi.string().allow(null, '').max(50).custom(commonValidatorWithSeperator).required().messages(generateCommonMessages('l')),
    lc:Joi.string().empty().max(50).custom(commonValidatorWithSeperator).required().messages(generateCommonMessages('lc')),
    ...CommonSchema

}).preferences(defaultJOIOptions)

export const LocationSchemaDelete = Joi.object({
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('WhCode'))
}).preferences(defaultJOIOptions)

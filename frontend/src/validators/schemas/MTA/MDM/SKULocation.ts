import Joi from "joi";
import { commonValidator, generateCommonMessages,defaultJOIOptions,MAX_CODE_LENGTH,MIN_DECIMAL_VAL,MAX_NAME_LENGTH,MAX_DECIMAL_VAL,CommonSchema,MAX_INT_VAL, commonValidatorWithSeperator} from "../../../commons";

const MIN_RLT_VALUE = 3;
const MIN_RCP_VALUE = 3;
const MIN_GCP_VALUE = 3;

const SKULocationMessages = (key: string) => ({
    "any.RLT": `${key} value should be greater than or equal to ${MIN_RLT_VALUE}`,
    "any.RCP": `${key} value should be greater than or equal to ${MIN_RCP_VALUE}`,
    "any.GCP": `${key} value should be greater than or equal to ${MIN_GCP_VALUE}`,
    "any.rcp": `${key} value should be greater than or equal to ${MIN_RCP_VALUE}`,
    "any.gcp": `${key} value should be greater than or equal to ${MIN_GCP_VALUE}`,
    "number.unsafe": `${key} should be less than ${MAX_INT_VAL}`,
    "any.mnwarn": "MinNorm should be greater than or equal to 2",
    "any.mnerror": "MinNorm should be greater than or equal to 0",
    "any.greaterthanZero": `${key} should be greater than 0`,
    "any.MinimumOrderCount": "Min Order Count should be greater than 0",
    'any.empty': `${key} should not be empty`,
    'any.FGRM': `${key} must be one of [fg, rm]`,
    'any.DBMACTIVE': `${key} must be one of ["YES", "NO", "Y", "N", "1", "0"]`
});


const ParentWhCodeValidator = (value:any,helper:any)=>{

    if(helper.prefs.context.wc === value) throw new Error('Source location code and destination location code are same');
    return commonValidatorWithSeperator(value,helper);

}

const RLTValidator = (value:any,helper:any)=>{
    if(!Number.isInteger(value)){
        return value
    }
    if(value <=0){
        return helper.error("any.greaterthanZero")
    }else if (value>0 && value <=2) {
        return helper.warn('any.RLT');
    }
    return value;
}

const RCPValidator = (value:any,helper:any)=>{
    if(!Number.isInteger(value)){
        return value
    }
    if(value <=0){
        return helper.error("any.greaterthanZero")
    }else if (value>0 && value <=2) {
        return helper.warn('any.RCP');
    }
    return value;
}

const GCPValidator = (value:any,helper:any)=>{
    if(!Number.isInteger(value)){
        return value
    }
    if(value <=0){
        return helper.error("any.greaterthanZero")
    }else if (value>0 && value <=2) {
        return helper.warn('any.GCP');
    }
    return value;
}

const OCPValidator = (value:any,helper:any)=>{
    if(!Number.isInteger(value)){
        return value
    }
    if(value <=0){
        return helper.error("any.greaterthanZero")
    }
    return value;
}

const MOCValidator = (value:any,helper:any)=>{
    if(!Number.isInteger(value)){
        return value
    }
    if(value <=0){
        return helper.error("any.MinimumOrderCount")
    }
    return value;
}


const MNValidator = (value:any,helper:any)=>{
    if(!Number.isInteger(value)){
        return value
    }
    if(value<0){
        return helper.error("any.mnerror")
    }
    // }else if(value<2){
    //     return helper.warn('any.mnwarn')
    // }
    return value
}



export const SKULocationSchema = Joi.object({
    SrNo:Joi.string(),
    sc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidatorWithSeperator).required().messages(generateCommonMessages('SKUCode')),
    sd:Joi.string().empty().max(MAX_NAME_LENGTH),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidatorWithSeperator).required().messages(generateCommonMessages('wc')),
    wd:Joi.string().empty().max(MAX_NAME_LENGTH),
    pwc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(ParentWhCodeValidator).required().messages(generateCommonMessages('pwc')),
    pd:Joi.string(),
    n:Joi.number().integer(),
    mn:Joi.number().integer().custom(MNValidator).messages(SKULocationMessages('mn')),
    rlt:Joi.number().integer().max(MAX_DECIMAL_VAL).custom(RLTValidator).messages(SKULocationMessages('RLT')),
    rcp:Joi.number().integer().max(MAX_DECIMAL_VAL).custom(RCPValidator).messages(SKULocationMessages('RCP')),
    gcp:Joi.number().integer().max(MAX_DECIMAL_VAL).custom(GCPValidator).messages(SKULocationMessages('GCP')),
    ocp:Joi.number().integer().max(MAX_INT_VAL).allow(null, '').custom(OCPValidator).messages(SKULocationMessages('OCP')),
    moc:Joi.number().integer().max(MAX_INT_VAL).allow(null, '').custom(MOCValidator).messages(SKULocationMessages('MinimumOrderCount')),
    ps:Joi.number().integer().min(1).max(MAX_INT_VAL).messages(SKULocationMessages('ps')),
    st:Joi.number().min(MIN_DECIMAL_VAL).max(MAX_DECIMAL_VAL).allow(null,'').messages({'number.unsafe':`Modified Spike Threshold should be less than ${MAX_DECIMAL_VAL}`}),
    dst:Joi.number().min(MIN_DECIMAL_VAL).max(MAX_DECIMAL_VAL).messages({'number.unsafe':`DefaultSpikeThreshold should be less than ${MAX_DECIMAL_VAL}`}),
    pt:Joi.number().min(MIN_DECIMAL_VAL).max(MAX_DECIMAL_VAL).allow(null,'').messages({'number.unsafe':`Modified PSO Threshold should be less than ${MAX_DECIMAL_VAL}`}),
    dpt:Joi.number().min(MIN_DECIMAL_VAL).max(MAX_DECIMAL_VAL).messages({'number.unsafe':`Default PSO Threshold should be less than ${MAX_DECIMAL_VAL}`}),
    npr:Joi.number().integer().min(0).max(100000000).allow(null,''),
    frf:Joi.string().valid("fg", "rm").insensitive().messages({'any.only':`"frf" must be one of [fg, rm]`,'string.base': `"frf" must be one of [fg, rm]`}), //make this case insensitive
    da:Joi.string().valid("yes", "no", "y", "n", 1, 0, "1", "0").insensitive().default(1).messages({'any.only':`"da" must be one of [yes, no, y, n, 1, 0]`, 'string.base': `"da" must be one of [yes, no, y, n, 1, 0]`}),
    spr:Joi.number().integer().min(0).max(100000000).allow(null,''),
    // NormPercentReservation:Joi.number().integer().min(0).max(100).default(0),
    ...CommonSchema

}).preferences(defaultJOIOptions)

export const SKULocationSchemaDelete = Joi.object({
    sc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('SKUCode')),
    wc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(commonValidator).required().messages(generateCommonMessages('WhCode')),
    pwc:Joi.string().empty().max(MAX_CODE_LENGTH).custom(ParentWhCodeValidator).required().messages({...generateCommonMessages('ParentWhCode')}),
}).preferences(defaultJOIOptions)
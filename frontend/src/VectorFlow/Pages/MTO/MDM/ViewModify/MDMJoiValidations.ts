import Joi from "joi";

const patternCode = /^[a-zA-Z0-9 _-]+$/;
const patternDesc = /^[a-zA-Z0-9/() _.,-]+$/;

export const BUFFER_VALIDATION_SCHEMA = Joi.object({
  bsz: Joi.number().integer().min(1).max(364).required().messages({
    "number.base": "Buffer Size must be a valid number.",
    "number.min": "Buffer Size must be at least {#limit}.",
    "number.max": "Buffer size cannot exceed for over a year.",
    "number.integer": "Buffer size must be an integer!",
    "any.required": "Enter the Buffer Size!",
    "number.unsafe": "Buffer size must be a safe number",

  }),

  slt: Joi.number().integer().min(0).max(364).required().messages({
    "number.base": "SLT must be a valid number.",
    "number.min": "SLT must be at least {#limit}.",
    "number.max": "SLT must be at most {#limit}.",
    "number.integer": "SLT must be an integer!",
    "any.required": "SLT cannot be empty!",
    "number.unsafe": "SLT must be a safe number",

  }),

  mlt: Joi.number().integer().min(0).max(364).required().messages({
    "number.base": "MLT must be a valid number.",
    "number.min": "MLT must be at least {#limit}.",
    "number.max": "MLT must be at most {#limit}.",
    "number.integer": "MLT must be an integer!",
    "any.required": "MLT cannot be empty!",
    "number.unsafe": "MLT must be a safe number",
  }),

  bt: Joi.required().messages({
    "any.required": "Enter the Buffer Type!",
  }),

  bcd: Joi.string().pattern(patternCode).max(100).required().messages({
    "string.base":"Enter a valid Buffer Code!",
    "string.pattern.base": "Buffer Code must contain only letters, numbers, underscores, and hyphens!",
    "string.max": "Buffer Code must be no more than 100 characters long!",
    "any.required": "Enter a valid Buffer Code!"
  }),

  bd: Joi.string().pattern(patternDesc).max(200).required().messages({
    "string.base":"Enter a valid Buffer Description!",
    "string.pattern.base": "Special characters are not permitted in the Buffer Description!",
    "string.max": "Buffer Description must be no more than 200 characters long!",
    "any.required": "Enter a valid Buffer Description!",
  }),

  ib: Joi.alternatives()
    .try(Joi.boolean(), Joi.string().valid("true", "false"))
    .required()
    .messages({
      "alternatives.types": "Is Blue must be either true or false!", 
      "boolean.base": "Is Blue must be either true or false!",
      "string.base": "Is Blue must be either true or false!",
      "any.only": "Is Blue must be either true or false!",
      "any.required": "Is Blue is required!",
      "alternatives.match": "Is Blue must be either true or false!" ,
    }),

  iv: Joi.boolean().allow(null).default(false).messages({
    "any.required": "Is Active must be either False or True",
    "boolean.base":"Is Active must be either False or True"

  }),

  editable: Joi.any().optional(),
  
  err : Joi.any().optional(),
  
  rid : Joi.any().optional(),

  bid: Joi.any().optional(),

  ia: Joi.optional(),

  iu: Joi.optional(),

  id : Joi.any().optional(),

  isdel : Joi.optional(),

});


export const CCR_VALIDATION_SCHEMA = Joi.object({

  cnm: Joi.string().pattern(patternDesc).max(200).required().messages({
    "string.base": "CCR name cannot be empty!",
    "string.pattern.base": "Special characters are not permitted in the CCR name!",
    "string.max": "CCR name must be no more than 200 characters long!",
    "any.required": "CCR name cannot be empty!",
  }),

  cgid: Joi.required().messages({
    "string.base":"CCR group cannot be empty!",
    "any.required": "Choose a valid ccrgroup from the dropdown!",
  }),

  cpd: Joi.number().min(1).required().messages({
    "number.base":"CCR Capacity Per Day must be a number!",
    "number.min": "CCR Capacity Per Day should be greater than 0!",
    "number.unsafe": "CCR Capacity Per Day must be a safe number",
    "any.required": "CCR Capacity Per Day cannot be empty!",
  }),

  cwl: Joi.number().min(1).required().messages({
    "number.base":"Cummulative WIP Limit (cwl) must be a number!",
    "any.required": "Cummulative WIP Limit (cwl) cannot be empty!",
    "number.min": "Cummulative WIP Limit (cwl) should be greater than 0!",
    "number.unsafe": "Cummulative WIP Limit (cwl) must be a safe number",
  }),

  dp: Joi.required().messages({
    "string.base":"Department cannot be empty!",
    "any.required": "Choose a valid department from the dropdown!",
  }),

  pl: Joi.required().messages({
    // "string.base":"Plant cannot be empty!",
    "any.required": "Choose a valid plant from the dropdown!",
  }),

  rb: Joi.number().min(0).max(1).required().messages({
    "number.base":"Residual Buffer must be a number!",
    "number.min": "Residual Buffer (rb) should be a value between 0 and 1!",
    "number.max": "Residual Buffer (rb) should be a value between 0 and 1!",
    "any.required": "Residual Buffer (rb) is required!",
    "number.unsafe": "Residual Buffer (rb) must be a safe number",
  }),

  sh: Joi.number().min(1).integer().required().messages({ 
      "number.base": "Scheduling Horizon must be a number!",
      "number.integer": "Scheduling Horizon must be an integer!",
      "any.required": "Scheduling Horizon cannot be empty!",
      "number.unsafe": "Scheduling Horizon must be a safe number",
      "number.min": "Scheduling Horizon should be greater than 1!",
    }),

  fh: Joi.number().min(Joi.ref('sh')).integer().required().messages({ 
    "number.base": "FOL Horizon must be a number!",
    "number.integer": "FOL Horizon must be an integer!",
    "any.required": "FOL Horizon cannot be empty!",
    "number.min": "Fol Horizon should be at least equal to the Scheduling Horizon.",
    "number.unsafe": "Fol Horizon must be a safe number",
  }),
    
  whpd: Joi.number()
    .min(1)
    .required()
    .messages({
      "number.base":"Working hours Per Day must be a number!",
      "any.required": "Working hours Per Day cannot be empty!",
      "number.min": "Working hours Per Day should be greater than 0!",
      "number.unsafe": "Working hours Per Day must be a safe number",
    }),
  ccd: Joi.string().pattern(patternCode).max(100).required().messages({
    "string.base": "CCR Code cannot be empty!",
    "string.pattern.base": "CCR Code must contain only letters, numbers, underscores, and hyphens!",
    "string.max": "CCR Code must be no more than 100 characters long!",
    "any.required": "CCR Code is required!"
    }),

  err : Joi.any().optional(),

  cid: Joi.any().default(null),
  a1: Joi.any().default(null),
  a2: Joi.any().default(null),
  a3: Joi.any().default(null),
  a4: Joi.any().default(null),
  a5: Joi.any().default(null),
  a6: Joi.any().default(null),
  a7: Joi.any().default(null),
  a8: Joi.any().default(null),
  a9: Joi.any().default(null),
  a10: Joi.any().default(null),
  iv: Joi.boolean().allow(null).default(false).messages({
    "boolean.base": "Is Active must be either true or false!",
    "any.required": "Is Active is required! It should be either true or false.",
  }),
  
  editable: Joi.any().optional(),
  rid: Joi.any().optional(),
  cgcd: Joi.any().optional(),
  cgm: Joi.any().optional(),
  plcd: Joi.any().optional(),
  plnm: Joi.any().optional(),
  dpcd: Joi.any().optional(),
  dpnm: Joi.any().optional(),
  did: Joi.any().optional(),
  cgnm: Joi.any().optional(),
  ia: Joi.optional(),

  iu: Joi.optional(),

  id : Joi.any().optional(),

  isdel : Joi.optional(),
});

export const CALENDAR_VALIDATION_SCHEMA = Joi.object({
  dow: Joi.array()
  .items(
    Joi.object({
      id: Joi.number().allow(null).messages({
        "number.base": "Id must be a number",
      }),
      mn: Joi.string().allow('').messages({
        "string.base": "Month type must be a string",
      }),
      md: Joi.string().allow('').messages({
        "string.base": "Month day must be a string",
      }),
    })
  )
  .optional(),

  plnm: Joi.string().required().messages({
    "string.base": "Plant name cannot be empty!",
    "any.required": "Plant name cannot be empty!",
    "string.empty": "Plant name cannot be empty!",
  }),

  rb: Joi.string().valid("Once", "Weekly", "Monthly").messages({
    "string.base": "Recurrence cannot be empty!",
    "any.required": "Recurrence cannot be empty!",
    "any.only": "Recurrence must be either Once, Weekly, or Monthly!",
  }),

  hid: Joi.any().optional(),

  rd : Joi.number().allow(null).max(4).optional().messages({
    "number.base": "Repeat duration must be a number!",
    "number.max": "Repeat duration cannot exceed {#limit}.",
    "any.required": "Repeat duration cannot be empty!",
  }),

  ccr: Joi.string().required().optional().messages({
    "string.base": "CCR cannot be empty!",
    "string.empty": "CCR cannot be empty!",
    "any.required": "CCR cannot be empty!",
  }),
  
  ccr_id: Joi.array().items(Joi.number()).messages({
    "string.base": "CCR Id cannot be empty!",
    "any.required": "CCR Id cannot be empty!",
  }),
 
  dsc: Joi.string().required().max(100).messages({
    "string.base": "Title cannot be empty!",
    "any.required": "Title cannot be empty!",
    "string.max": "Title cannot exceed 100 characters!",
    "string.empty": "Title cannot be empty!",
  }),

  sd: Joi.date()
    .required()
    .min(new Date()) // start date should be greater than today or equal to today's date
    .messages({
      "date.base": "Start date cannot be empty!",
      "any.required": "Start date cannot be empty!",
      "date.less": "Start date must be less than End date!",
      "date.min": "start date must be equal to or greater then Today"
    }),
  
  ed: Joi.date()
    .required()
    .min(Joi.ref('sd')) // ✅ Allows ed >= sd
    .messages({
      "date.base": "End date cannot be empty!",
      "any.required": "End date cannot be empty!",
      "date.min": "End date must be equal to or after Start date!",
  }),
  
  iwd: Joi.boolean().required().messages({
    "boolean.base": "Is Working Day must be either true or false!",
    "any.required": "Is Working Day is required!",

  }),

  plid: Joi.number().allow(null).messages({
    "number.base": "Plant Id cannot be empty!",
    "any.required": "Plant Id cannot be empty!",
  }),

  err: Joi.object({
    error: Joi.string().allow("").optional(),
    warning: Joi.string().allow("").optional(),
  }),

  ia: Joi.boolean().default(false).optional(),
  iu: Joi.boolean().default(false).optional(),
  id: Joi.boolean().default(false).optional(),

});

export const CALENDAR_Add_VALIDATION_SCHEMA = Joi.object({
  dow: Joi.any(),

  plnm: Joi.string().required().optional().messages({
    "string.base": "Plant name cannot be empty!",
    "any.required": "Plant name cannot be empty!",
    "string.empty": "Plant name cannot be empty!",
  }),

  rb: Joi.any(),

  hid: Joi.any().optional(),

  rd : Joi.any(),

  ccr: Joi.string().required().optional().messages({
    "string.base": "CCR cannot be empty!",
    "string.empty": "CCR cannot be empty!",
    "any.required": "CCR cannot be empty!",
  }),
  
  ccr_id: Joi.any(),
 
  dsc: Joi.string().required().max(100).messages({
    "string.base": "Title cannot be empty!",
    "any.required": "Title cannot be empty!",
    "string.max": "Title cannot exceed 100 characters!",
    "string.empty": "Title cannot be empty!",
  }),

  sd: Joi.date()
    .required()
    .messages({
      "date.base": "Start date cannot be empty!",
      "any.required": "Start date cannot be empty!",
      "date.less": "Start date must be less than End date!",
    }),
  
    ed: Joi.date()
    .required()
    .min(Joi.ref('sd')) // ✅ Allows ed >= sd
    .messages({
      "date.base": "End date cannot be empty!",
      "any.required": "End date cannot be empty!",
      "date.min": "End date must be equal to or after Start date!",
    }),
  
  iwd: Joi.boolean().required().messages({
    "boolean.base": "Is Working Day must be either true or false!",
    "any.required": "Is Working Day is required!",

  }),

  plid: Joi.number().allow(null).optional().messages({
    "number.base": "Plant Id cannot be empty!",
    "any.required": "Plant Id cannot be empty!",
  }),

  err: Joi.object({
    error: Joi.string().allow("").optional(),
    warning: Joi.string().allow("").optional(),
  }),

  ia: Joi.boolean().default(false).optional(),
  iu: Joi.boolean().default(false).optional(),
  id: Joi.boolean().default(false).optional(),
  rid: Joi.any(),
  did: Joi.any(),

});


// export const POOGI_VALIDATION_SCHEMA = Joi.object({
//   plnm: Joi.string().min(1).required().messages({
//     'string.empty': 'Plant name cannot be empty!',
//     'any.required': 'Plant name cannot be empty!',
//   }),

//   majdsc: Joi.string().allow('', null).when('mindsc', {
//     is: Joi.string().min(1), 
//     then: Joi.string().min(1).required().messages({
//       'string.empty': 'State the major reason to which the minor reason belongs!',
//       'any.required': 'State the major reason to which the minor reason belongs!',
//     }),
//   }).messages({
//     'string.empty': 'Major reason description cannot be empty!',
//     'any.required': 'Major reason description cannot be empty!',
//   }),

//   mindsc: Joi.string().allow('', null).when('majdsc', {
//     is: Joi.string().min(1),
//     then: Joi.string().min(1).required().messages({
//       'string.empty': 'Each major reason must have at least one minor reason!',
//       'any.required': 'Each major reason must have at least one minor reason!',
//     }),
//   }),

//   majcd : Joi.string(),

//   mincd : Joi.string(),

//   err : Joi.object({
//     error: Joi.string().allow("").optional(), 
//     warning: Joi.string().allow("").optional(),
//   }).optional(),

// });
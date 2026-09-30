def construct_response_code(prefix_code, code_type, code_number, msg):
    prefix_code = str(prefix_code)
    code_type = str(code_type)
    code_number = str(code_number)
    code = '_'.join([prefix_code, code_type, code_number])
    return {
        'code': code,
        "msg": msg
    }


class ResponseCode:
    SUCCESS = 200
    FAIL = 403
    BAD_REQUEST = 400

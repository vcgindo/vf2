"""Strict BTR response comparison with the human-approved April7 Category exception.

This is benchmark evidence only. Never modify application responses or transfer
the exception to accepted normal publications or other datasets/reports.
"""
from collections import Counter
import re

MANIFEST = 'afe42593ca2abdf5e2395433ac70834723f4eac1dfa5a2982192c7688906b836'


def compare(legacy, fresh, *, manifest_sha256, business_date, route):
    if (manifest_sha256, business_date, route) != (MANIFEST, '2026-04-07', 'GetBTRData'):
        raise ValueError('Category presentation exception does not cover this boundary')
    differences=[];exceptions=[]
    def visit(left,right,path):
        if type(left) is not type(right):
            differences.append(dict(path=path,reason='type',legacy_type=type(left).__name__,fresh_type=type(right).__name__))
        elif isinstance(left,dict):
            for key in sorted(set(left)|set(right)):
                location=path+'/'+key
                if key not in left or key not in right:
                    differences.append(dict(path=location,reason='missing_field'))
                else:visit(left[key],right[key],location)
        elif isinstance(left,list):
            if len(left)!=len(right):differences.append(dict(path=path,reason='length',legacy=len(left),fresh=len(right)))
            for index,(a,b) in enumerate(zip(left,right)):visit(a,b,path+'/'+str(index))
        elif left!=right:
            if (isinstance(left,str) and re.fullmatch(r'/data/(tech|eco)/\d+/Category',path)
                    and left and right and Counter(left.split('|'))==Counter(right.split('|'))):
                exceptions.append(dict(path=path,legacy=left,fresh=right))
            else:differences.append(dict(path=path,reason='value',legacy=left,fresh=right))
    visit(legacy,fresh,'')
    return dict(status='FAIL' if differences else 'PASS_WITH_APPROVED_CATEGORY_ORDER' if exceptions else 'PASS_STRICT',
                exact_response_equal=legacy==fresh,differences=differences,category_order_exceptions=exceptions)

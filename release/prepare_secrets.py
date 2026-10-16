"""Create NEW deployment secrets privately; never replace existing keys or credentials."""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets


def prepare(directory, public_cipher_key=None):
    # Imported only by the auth-image operator command, where the pinned existing
    # crypto dependency is installed. It never contacts a serving auth account.
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_OAEP
    from Crypto.Hash import SHA256
    directory=Path(directory).resolve()
    if directory.exists():
        raise ValueError('Secrets destination already exists; key/credential replacement prohibited')
    directory.mkdir(parents=True,mode=0o700)
    directory.chmod(0o700)
    values={name:secrets.token_urlsafe(48) for name in
        ['postgres_admin_password','mta_secret','auth_secret','mto_secret',
         *[service+'_'+role+'_password' for service in ('mta','mto','auth') for role in ('installer','runtime')]]}
    key=RSA.generate(2048)
    values['auth_private_key']=key.export_key(format='PEM',pkcs=8).decode()
    values['auth_public_key']=key.public_key().export_key().decode()
    for role in ('installer','runtime'):
        values['auth_'+role+'_password_enc']=base64.b64encode(PKCS1_OAEP.new(key.public_key(),hashAlgo=SHA256).encrypt(values['auth_'+role+'_password'].encode())).decode()
    for name,value in values.items():
        # Private parent0700 protects the host directory. Individual read-only
        # secret mounts must be readable by their nonroot service UID; only the
        # declared service receives each file, never a shared secrets directory.
        descriptor=os.open(directory/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
        with os.fdopen(descriptor,'w',encoding='utf-8') as stream:
            stream.write(value+'\n')
    return dict(status='NEW_SECRET_FILES_CREATED_NO_DATABASE_OR_ACCOUNT_OPERATION',
        files=sorted(values),public_client_cipher_key=public_cipher_key or secrets.token_urlsafe(24),
        qualification='Client cipher key is embedded public build configuration; keep signing/database/RSA private values out of .env build arguments and images.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True,type=Path)
    parser.add_argument('--public-client-cipher-key')
    args=parser.parse_args()
    print(json.dumps(prepare(args.directory,args.public_client_cipher_key),sort_keys=True))

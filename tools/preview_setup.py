"""Create isolated preview configuration once; never reset an existing login."""
import secrets
from pathlib import Path


def main():
    root = Path('D:/freshvcf-build/preview')
    root.mkdir(exist_ok=True)
    (root / 'secrets').mkdir(exist_ok=True)
    path = root / 'preview.env'
    if path.exists():
        print(f'Keeping existing preview configuration: {path}')
        return
    values = {
        'PREVIEW_SECRET_KEY': secrets.token_hex(40),
        'PREVIEW_CLIENT_KEY': secrets.token_hex(16),
        'PREVIEW_USERNAME': 'fresh.preview@vectorflow.local',
        'PREVIEW_PASSWORD': 'F3!' + secrets.token_hex(5),
    }
    with path.open('x', encoding='utf-8') as stream:
        stream.write(''.join(f'{key}={value}\n' for key, value in values.items()))
    print(f'Created local test-only preview configuration: {path}')


if __name__ == '__main__':
    main()

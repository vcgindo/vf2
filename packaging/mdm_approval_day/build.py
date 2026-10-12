"""Freeze the finite MDM-day package using the existing verified image builder."""
import importlib.util
from pathlib import Path


def main():
    path = Path(__file__).resolve().parents[1] / 'cohort6' / 'build.py'
    spec = importlib.util.spec_from_file_location('mdm_day_image_builder', path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.BASE_TAG = 'freshvcf-cohort6:preparation-001'
    builder.BASE_ID = 'sha256:aad2a0a211b3435d0c9528457c6d24f61c9825673993f52df45a5c02eca72673'
    builder.ROOTS += [
        'user-service/api', 'user-service/apps', 'user-service/common',
        'tools/mdm_approval_day_settings.py',
        'tools/mdm_approval_day_identity.py',
        'tools/mdm_approval_day_workflow.py',
        'packaging/mdm_approval_day/execute-day.sh',
    ]
    builder.main()


if __name__ == '__main__':
    main()

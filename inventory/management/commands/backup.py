from django.core.management.base import BaseCommand
from django.conf import settings
import os
import subprocess
from datetime import datetime

class Command(BaseCommand):
    help = 'Backup PostgreSQL database'

    def handle(self, *args, **options):
        # Ensure backup directory exists
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # database config
        db = settings.DATABASES['default']
        db_name = db['NAME']
        db_user = db['USER']
        db_host = db['HOST']
        db_port = db['PORT']
        db_password = db['PASSWORD']
        
        # Timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sql')
        
        # PostgreSQL dump command
        pg_dump_path = getattr(settings, 'PG_DUMP_PATH', 'pg_dump')
        
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password
        
        command = [
            pg_dump_path,
            '-h', db_host,
            '-p', db_port,
            '-U', db_user,
            '-F', 'c',  # Custom format (compressed)
            '-b',       # Include large objects
            '-v',       # Verbose
            '-f', backup_file,
            db_name
        ]
        
        try:
            self.stdout.write(f'Starting backup of {db_name}...')
            subprocess.run(command, env=env, check=True)
            self.stdout.write(self.style.SUCCESS(f'Backup created: {backup_file}'))
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f'Backup failed: {e}'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'pg_dump not found at {pg_dump_path}'))

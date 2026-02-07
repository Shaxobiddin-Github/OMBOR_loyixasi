"""
Database backup command using pg_dump.
Supports Windows with configurable PG_DUMP_PATH.
"""
import os
import subprocess
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create PostgreSQL database backup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Custom output file path'
        )

    def handle(self, *args, **options):
        # Get pg_dump path
        pg_dump = getattr(settings, 'PG_DUMP_PATH', 'pg_dump')
        
        # Check if pg_dump exists (if custom path specified)
        if pg_dump != 'pg_dump' and not os.path.exists(pg_dump):
            raise CommandError(
                f"pg_dump topilmadi: {pg_dump}\n"
                f"settings.py da PG_DUMP_PATH ni to'g'ri sozlang.\n"
                f"Misol: PG_DUMP_PATH = r'C:\\Program Files\\PostgreSQL\\15\\bin\\pg_dump.exe'"
            )
        
        # Get database config
        db = settings.DATABASES['default']
        
        if db['ENGINE'] != 'django.db.backends.postgresql':
            raise CommandError("Bu command faqat PostgreSQL uchun ishlaydi")
        
        # Create backup directory
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate filename
        if options.get('output'):
            filepath = options['output']
        else:
            filename = f"backup_{datetime.now():%Y%m%d_%H%M%S}.sql"
            filepath = os.path.join(backup_dir, filename)
        
        # Build pg_dump command
        cmd = [
            pg_dump,
            f"--host={db.get('HOST', 'localhost')}",
            f"--port={db.get('PORT', '5432')}",
            f"--username={db['USER']}",
            f"--dbname={db['NAME']}",
            f"--file={filepath}",
            "--no-password",  # Use PGPASSWORD env var
        ]
        
        # Set password via environment
        env = os.environ.copy()
        env['PGPASSWORD'] = db['PASSWORD']
        
        self.stdout.write(f"Backup yaratilmoqda: {filepath}")
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Get file size
            size_bytes = os.path.getsize(filepath)
            size_mb = size_bytes / (1024 * 1024)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Backup muvaffaqiyatli yaratildi!\n"
                    f"   Fayl: {filepath}\n"
                    f"   Hajmi: {size_mb:.2f} MB"
                )
            )
            
        except FileNotFoundError:
            raise CommandError(
                "pg_dump topilmadi. PostgreSQL o'rnatilganligini tekshiring.\n"
                "Windows'da PG_DUMP_PATH ni settings.py'da sozlang:\n"
                "PG_DUMP_PATH = r'C:\\Program Files\\PostgreSQL\\15\\bin\\pg_dump.exe'"
            )
        except subprocess.CalledProcessError as e:
            raise CommandError(
                f"Backup yaratishda xato:\n{e.stderr}"
            )

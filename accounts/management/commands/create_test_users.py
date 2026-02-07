"""
Create test users for development/testing.
"""
from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create test users with different roles'

    def handle(self, *args, **options):
        test_users = [
            {'username': 'admin_test', 'password': 'test1234', 'role': 'admin'},
            {'username': 'operator1', 'password': 'test1234', 'role': 'operator'},
            {'username': 'operator2', 'password': 'test1234', 'role': 'operator'},
            {'username': 'viewer1', 'password': 'test1234', 'role': 'viewer'},
        ]
        
        for data in test_users:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'role': data['role'],
                    'is_staff': data['role'] == 'admin',
                }
            )
            if created:
                user.set_password(data['password'])
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Created: {data['username']} ({data['role']})")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⏭️ Exists: {data['username']}")
                )
        
        self.stdout.write("\n📋 Barcha test userlar:")
        self.stdout.write("-" * 40)
        for data in test_users:
            self.stdout.write(f"  {data['username']} / {data['password']} ({data['role']})")

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('recipient', models.EmailField()),
                ('subject', models.CharField(max_length=300)),
                ('email_type', models.CharField(
                    choices=[
                        ('welcome',        'Welcome'),
                        ('password_reset', 'Password Reset'),
                        ('match_alert',    'Match Alert'),
                        ('contact',        'Contact Owner'),
                        ('claim_approved', 'Claim Approved'),
                        ('claim_rejected', 'Claim Rejected'),
                        ('handover',       'Handover Confirmation'),
                        ('other',          'Other'),
                    ],
                    db_index=True, default='other', max_length=30,
                )),
                ('status', models.CharField(
                    choices=[('sent', 'Sent'), ('failed', 'Failed')],
                    db_index=True, default='sent', max_length=20,
                )),
                ('error_message', models.TextField(blank=True)),
                ('sent_at', models.DateTimeField(
                    db_index=True, default=django.utils.timezone.now)),
                ('recipient_user', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='email_logs',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-sent_at']},
        ),
    ]

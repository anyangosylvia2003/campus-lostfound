import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('security', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # CustodyRecord — retention_deadline
        migrations.AddField(
            model_name='custodyrecord',
            name='retention_deadline',
            field=models.DateField(blank=True, null=True, help_text='Date after which item should be reviewed for disposal.'),
        ),
        # ClaimRequest — QR handover token
        migrations.AddField(
            model_name='claimrequest',
            name='handover_token',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AddField(
            model_name='claimrequest',
            name='handover_token_used',
            field=models.BooleanField(default=False),
        ),
        # HandoverLog — qr_verified flag
        migrations.AddField(
            model_name='handoverlog',
            name='qr_verified',
            field=models.BooleanField(default=False),
        ),
        # New CustodyTransferLog model
        migrations.CreateModel(
            name='CustodyTransferLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_location', models.CharField(max_length=200)),
                ('to_location', models.CharField(max_length=200)),
                ('transferred_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('reason', models.TextField(blank=True)),
                ('custody', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfers', to='security.custodyrecord')),
                ('transferred_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='custody_transfers', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-transferred_at']},
        ),
    ]

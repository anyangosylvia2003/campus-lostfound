from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='brand',
            field=models.CharField(blank=True, help_text='e.g. Samsung, HP, Nike', max_length=100),
        ),
        migrations.AddField(
            model_name='item',
            name='color',
            field=models.CharField(blank=True, help_text='e.g. Black, Blue, Red/White', max_length=100),
        ),
        migrations.AddField(
            model_name='item',
            name='location_detail',
            field=models.CharField(blank=True, help_text='Extra detail, e.g. "near the window on floor 2"', max_length=200),
        ),
        migrations.AddField(
            model_name='item',
            name='time_of_day',
            field=models.TimeField(blank=True, help_text='Approximate time (optional)', null=True),
        ),
        migrations.AddField(
            model_name='item',
            name='retention_days',
            field=models.PositiveIntegerField(default=60, help_text='Days to hold before disposal review'),
        ),
        migrations.AlterField(
            model_name='item',
            name='category',
            field=models.CharField(
                choices=[
                    ('electronics', 'Electronics'),
                    ('documents', 'Documents / Certificates'),
                    ('ids', 'ID / Student Card'),
                    ('keys', 'Keys'),
                    ('wallets', 'Wallet / Purse'),
                    ('bags', 'Bag / Backpack'),
                    ('clothing', 'Clothing'),
                    ('others', 'Others'),
                ],
                db_index=True, max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='item',
            name='status',
            field=models.CharField(
                choices=[
                    ('active', 'Active'),
                    ('matched', 'Matched'),
                    ('claimed', 'Claimed — Pending Verification'),
                    ('resolved', 'Resolved / Returned'),
                    ('donated', 'Donated / Disposed'),
                ],
                db_index=True, default='active', max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='item',
            name='location',
            field=models.CharField(
                choices=[
                    ('', 'Select a location...'),
                    ('Main Gate', 'Main Gate'),
                    ('Library', 'Library'),
                    ('Student Centre', 'Student Centre'),
                    ('Cafeteria / Dining Hall', 'Cafeteria / Dining Hall'),
                    ('Admin Block', 'Admin Block'),
                    ('Science Block', 'Science Block'),
                    ('Engineering Block', 'Engineering Block'),
                    ('Arts Block', 'Arts Block'),
                    ('Business Block', 'Business Block'),
                    ('ICT Lab', 'ICT Lab'),
                    ('Sports Complex / Field', 'Sports Complex / Field'),
                    ('Gym', 'Gym'),
                    ('Auditorium / Hall', 'Auditorium / Hall'),
                    ('Chapel / Prayer Room', 'Chapel / Prayer Room'),
                    ('Health Centre / Clinic', 'Health Centre / Clinic'),
                    ('Hostel Block A', 'Hostel Block A'),
                    ('Hostel Block B', 'Hostel Block B'),
                    ('Hostel Block C', 'Hostel Block C'),
                    ('Parking Lot', 'Parking Lot'),
                    ('Bus / Matatu Stage', 'Bus / Matatu Stage'),
                    ('ATM / Finance Office', 'ATM / Finance Office'),
                    ('Lecture Hall 1', 'Lecture Hall 1'),
                    ('Lecture Hall 2', 'Lecture Hall 2'),
                    ('Lecture Hall 3', 'Lecture Hall 3'),
                    ('Other / Unknown', 'Other / Unknown'),
                ],
                db_index=True, max_length=200,
            ),
        ),
    ]

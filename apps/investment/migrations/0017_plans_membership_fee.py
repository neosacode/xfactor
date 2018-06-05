# Generated by Django 2.0.1 on 2018-06-05 15:06

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0016_remove_comissions_graduation'),
    ]

    operations = [
        migrations.AddField(
            model_name='plans',
            name='membership_fee',
            field=models.DecimalField(decimal_places=8, default=Decimal('0.00'), max_digits=20, verbose_name='Membership Fee'),
        ),
    ]

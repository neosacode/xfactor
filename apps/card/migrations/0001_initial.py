# Generated by Django 2.0.1 on 2018-07-19 18:25

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('exchange_core', '0002_historicalaccounts_historicalbankaccounts_historicalbankwithdraw_historicalcryptowithdraw_historical'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cards',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('number', models.CharField(max_length=16)),
                ('name', models.CharField(max_length=50)),
                ('document_1', models.CharField(max_length=30, null=True)),
                ('document_2', models.CharField(max_length=30, null=True)),
                ('birth_date', models.DateField(null=True)),
                ('mothers_name', models.CharField(max_length=50, null=True)),
                ('fathers_name', models.CharField(max_length=50, null=True)),
                ('is_active', models.BooleanField(default=False)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cards', to='exchange_core.Accounts')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]

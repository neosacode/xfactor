# Generated by Django 2.0.1 on 2018-05-26 19:34

from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('exchange_core', '0039_auto_20180525_1552'),
        ('investment', '0011_investments_membership_fee'),
    ]

    operations = [
        migrations.CreateModel(
            name='Credits',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('status', model_utils.fields.StatusField(choices=[('pending', 'pending'), ('paid', 'paid')], default='pending', max_length=100, no_check_for_status=True, verbose_name='status')),
                ('status_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='status', verbose_name='status changed')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('borrowed_amount', models.DecimalField(decimal_places=8, max_digits=20)),
                ('interest_percent', models.DecimalField(decimal_places=8, default=Decimal('0.00'), max_digits=20)),
                ('total_amount', models.DecimalField(decimal_places=8, default=Decimal('0.00'), max_digits=20)),
                ('receipt_date', models.DateField(blank=True, null=True)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='credits', to='exchange_core.Accounts', verbose_name='Account')),
            ],
            options={
                'verbose_name': 'Credit',
                'verbose_name_plural': 'Credits',
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='Installments',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('status', model_utils.fields.StatusField(choices=[('pending', 'pending'), ('paid', 'paid')], default='pending', max_length=100, no_check_for_status=True, verbose_name='status')),
                ('status_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='status', verbose_name='status changed')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('order', models.IntegerField(default=1)),
                ('due_date', models.DateField()),
                ('interest_percent', models.DecimalField(decimal_places=8, max_digits=20)),
                ('amount', models.DecimalField(decimal_places=8, max_digits=20)),
                ('receipt_date', models.DateField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Installment',
                'verbose_name_plural': 'Installments',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='Loans',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('status', model_utils.fields.StatusField(choices=[('pending', 'pending'), ('paid', 'paid')], default='pending', max_length=100, no_check_for_status=True, verbose_name='status')),
                ('status_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='status', verbose_name='status changed')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('borrowed_amount', models.DecimalField(decimal_places=8, max_digits=20)),
                ('total_amount', models.DecimalField(decimal_places=8, default=Decimal('0.00'), max_digits=20)),
                ('times', models.IntegerField(default=1)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loans', to='exchange_core.Accounts', verbose_name='Account')),
            ],
            options={
                'verbose_name': 'Loan',
                'verbose_name_plural': 'Loans',
            },
        ),
        migrations.AddField(
            model_name='installments',
            name='loan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='installments', to='investment.Loans', verbose_name='Statement'),
        ),
    ]

# Generated by Django 3.1.6 on 2021-03-21 08:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_auto_20210321_0823'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='server',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='main.server'),
            preserve_default=False,
        ),
    ]

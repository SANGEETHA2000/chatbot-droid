# Generated by Django 5.1.6 on 2025-02-18 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_message_message_id_message_processed_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='message_id',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]

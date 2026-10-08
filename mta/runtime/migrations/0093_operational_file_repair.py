import django.db.models.deletion
from django.db import migrations,models


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0092_operational_worker_lease')]
    operations=[
        migrations.AddField(model_name='operationalattempt',name='repair_of',field=models.ForeignKey(
            null=True,on_delete=django.db.models.deletion.PROTECT,related_name='repairs',to='fresh_mta.operationalattempt')),
        migrations.CreateModel(name='OperationalRepairTarget',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('ordinal',models.PositiveIntegerField()),
            ('equivalence',models.CharField(default='',max_length=24)),
            ('attempt',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='repair_targets',to='fresh_mta.operationalattempt')),
            ('original_file',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='repair_targets',to='fresh_mta.operationalfile')),
            ('replacement_file',models.OneToOneField(null=True,on_delete=django.db.models.deletion.PROTECT,related_name='replacement_target',to='fresh_mta.operationalfile')),
        ],options={'constraints':[
            models.UniqueConstraint(fields=('attempt','ordinal'),name='op_repair_target_ordinal'),
            models.UniqueConstraint(fields=('attempt','original_file'),name='op_repair_target_file'),
        ]}),
    ]

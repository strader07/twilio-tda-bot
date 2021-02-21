from django.db import models

# Create your models here.
class TradeOptions(models.Model):
    num_options = models.IntegerField(default=1)
    amt_options = models.FloatField(default=200)
    amt_shares = models.FloatField(default=200)
    last_modified = models.DateTimeField(auto_now_add = True)

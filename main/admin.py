from django.contrib import admin
from main.models import TradeOptions

# Register your models here.
@admin.register(TradeOptions)
class TradeOptionsAdmin(admin.ModelAdmin):
    list_display = ('num_options', 'amt_options', 'amt_shares')

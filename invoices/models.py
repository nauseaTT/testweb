from django.db import models

class Invoices(models.Model):
    code = models.CharField(max_length=10, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    personnel_id = models.CharField(max_length=20, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_teacher = models.IntegerField(blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    has_check = models.IntegerField(blank=True, null=True)
    has_guarantor = models.IntegerField(blank=True, null=True)
    guarantor_full_name = models.CharField(max_length=200, blank=True, null=True)
    guarantor_id = models.CharField(max_length=20, blank=True, null=True)
    prepayment = models.BigIntegerField(blank=True, null=True)
    installment_count = models.IntegerField(blank=True, null=True)
    paid_installments = models.IntegerField(blank=True, null=True)
    remaining_debt = models.BigIntegerField(blank=True, null=True)
    last_payment_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    total_paid = models.BigIntegerField(default=0, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'invoices'

class InvoiceItems(models.Model):
    invoice = models.ForeignKey('Invoices', models.DO_NOTHING, blank=True, null=True)
    product_description = models.CharField(max_length=255, blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)
    unit_price = models.BigIntegerField(blank=True, null=True)
    total_price = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'invoice_items'

class Payments(models.Model):
    invoice = models.ForeignKey('Invoices', models.DO_NOTHING)
    payment_type = models.CharField(max_length=20, choices=[
        ('installment', 'پرداخت قسط'),
        ('partial', 'پرداخت علی‌الحساب'),
        ('full', 'تسویه کامل')
    ])
    amount = models.BigIntegerField()
    payment_date = models.DateField()
    number_of_installments = models.IntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    transaction_id = models.CharField(max_length=50, blank=True, null=True)  # کد پیگیری
    card_number = models.CharField(max_length=19, blank=True, null=True)  # شماره کارت (مثل 1234-5678-9012-3456)

    class Meta:
        managed = False
        db_table = 'payments'
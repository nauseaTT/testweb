import math
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Invoices, InvoiceItems, Payments

def search_invoices(request):
    invoices = None
    search_type = None
    search_value = None
    if request.method == 'POST':
        search_type = request.POST.get('search_type')
        search_value = request.POST.get('search_value')

        if search_type == 'code':
            invoices = Invoices.objects.filter(code__icontains=search_value)
        elif search_type == 'personnel_id':
            invoices = Invoices.objects.filter(personnel_id__icontains=search_value)
        elif search_type == 'phone':
            invoices = Invoices.objects.filter(phone_number__icontains=search_value)
        elif search_type == 'name':
            invoices = Invoices.objects.filter(
                Q(first_name__icontains=search_value) |
                Q(last_name__icontains=search_value)
            )
        elif search_type == 'product':
            matching_items = InvoiceItems.objects.filter(product_description__icontains=search_value)
            invoice_ids = matching_items.values_list('invoice_id', flat=True)
            invoices = Invoices.objects.filter(id__in=invoice_ids)

        if invoices:
            for invoice in invoices:
                invoice.items = InvoiceItems.objects.filter(invoice=invoice)
                invoice.payments = Payments.objects.filter(invoice=invoice)
                invoice.payment_history = list(invoice.payments.values(
                    'payment_type', 'amount', 'number_of_installments', 'payment_date', 'notes', 'transaction_id', 'card_number'
                ))
                for payment in invoice.payment_history:
                    payment['type'] = dict(Payments._meta.get_field('payment_type').choices).get(payment['payment_type'], payment['payment_type'])
                    payment['date'] = payment.pop('payment_date')
                if invoice.prepayment and invoice.prepayment > 0:
                    invoice.payment_history.insert(0, {
                        'type': 'پیش‌پرداخت',
                        'amount': invoice.prepayment,
                        'number_of_installments': 0,
                        'date': None,
                        'notes': 'پیش‌پرداخت فاکتور',
                        'transaction_id': None,
                        'card_number': None
                    })
        else:
            messages.error(request, 'فاکتوری برای این معیار یافت نشد.')

    return render(request, 'invoices/search.html', {
        'invoices': invoices,
        'search_type': search_type,
        'search_value': search_value
    })

def process_payment(request, invoice_id):
    try:
        invoice = Invoices.objects.get(id=invoice_id)
    except Invoices.DoesNotExist:
        messages.error(request, 'فاکتور مورد نظر یافت نشد.')
        return redirect('search_invoices')

    remaining_installments = (invoice.installment_count or 0) - (invoice.paid_installments or 0)
    remaining_installments = max(0, remaining_installments)

    total_amount = (invoice.remaining_debt or 0) + (invoice.total_paid or 0) + (invoice.prepayment or 0)
    actual_payments = sum(payment.amount for payment in Payments.objects.filter(invoice=invoice))
    actual_remaining_debt = total_amount - (invoice.prepayment or 0) - actual_payments
    installment_amount = math.ceil(actual_remaining_debt / remaining_installments) if remaining_installments > 0 else 0

    if request.method == 'POST':
        payment_type = request.POST.get('payment_type')
        payment_amount = request.POST.get('payment_amount')
        number_of_installments = request.POST.get('number_of_installments', 1)
        payment_source = request.POST.get('payment_source')
        transaction_id = request.POST.get('transaction_id')
        card_number = request.POST.get('card_number')
        manual_transaction_id = request.POST.get('manual_transaction_id')
        manual_card_number = request.POST.get('manual_card_number')

        try:
            payment_amount = int(payment_amount.replace(',', '')) if payment_amount else 0
            number_of_installments = int(number_of_installments)

            if payment_amount <= 0:
                messages.error(request, 'مبلغ پرداخت باید بیشتر از صفر باشد.')
                return redirect('process_payment', invoice_id=invoice_id)

            final_transaction_id = transaction_id if payment_source == 'pos' else manual_transaction_id
            final_card_number = card_number if payment_source == 'pos' else manual_card_number
            if final_card_number:
                final_card_number = final_card_number.replace('-', '')

            payment_record = {
                'invoice': invoice,
                'payment_type': payment_type,
                'amount': payment_amount,
                'payment_date': timezone.now().date(),
                'number_of_installments': number_of_installments,
                'notes': '',
                'transaction_id': final_transaction_id,
                'card_number': final_card_number
            }

            if payment_type == 'installment':
                if remaining_installments <= 0:
                    messages.error(request, 'هیچ قسطی برای پرداخت باقی نمانده است.')
                    return redirect('process_payment', invoice_id=invoice_id)

                invoice.paid_installments += number_of_installments
                invoice.remaining_debt -= payment_amount
                invoice.total_paid += payment_amount
                invoice.last_payment_date = timezone.now().date()
                payment_record['notes'] = f'پرداخت {number_of_installments} قسط'

            elif payment_type == 'partial':
                invoice.remaining_debt -= payment_amount
                invoice.total_paid += payment_amount
                invoice.last_payment_date = timezone.now().date()
                payment_record['notes'] = 'پرداخت علی‌الحساب'

            elif payment_type == 'full':
                if payment_amount < invoice.remaining_debt:
                    messages.error(request, f'مبلغ پرداخت باید حداقل {invoice.remaining_debt:,} ريال باشد برای تسویه کامل.')
                    return redirect('process_payment', invoice_id=invoice_id)

                invoice.remaining_debt = 0
                invoice.total_paid += payment_amount
                invoice.paid_installments = invoice.installment_count
                invoice.last_payment_date = timezone.now().date()
                payment_record['notes'] = 'تسویه کامل فاکتور'

            if invoice.remaining_debt <= 0:
                invoice.status = 'تسویه'
                invoice.installment_count = invoice.paid_installments

            invoice.save()
            Payments.objects.create(**payment_record)
            messages.success(request, 'پرداخت با موفقیت ثبت شد.')
            return redirect('search_invoices')

        except ValueError as e:
            messages.error(request, f'ورودی نامعتبر: لطفاً مقادیر عددی صحیح وارد کنید. ({str(e)})')
            return redirect('process_payment', invoice_id=invoice_id)
        except Exception as e:
            messages.error(request, f'خطایی رخ داد: {str(e)}')
            return redirect('process_payment', invoice_id=invoice_id)

    payments = Payments.objects.filter(invoice=invoice)
    payment_history = list(payments.values(
        'payment_type', 'amount', 'number_of_installments', 'payment_date', 'notes', 'transaction_id', 'card_number'
    ))
    for payment in payment_history:
        payment['type'] = dict(Payments._meta.get_field('payment_type').choices).get(payment['payment_type'], payment['payment_type'])
        payment['date'] = payment.pop('payment_date')
    if invoice.prepayment and invoice.prepayment > 0:
        payment_history.insert(0, {
            'type': 'پیش‌پرداخت',
            'amount': invoice.prepayment,
            'number_of_installments': 0,
            'date': None,
            'notes': 'پیش‌پرداخت فاکتور',
            'transaction_id': None,
            'card_number': None
        })

    return render(request, 'invoices/payment.html', {
        'invoice': invoice,
        'payment_history': payment_history,
        'remaining_installments': remaining_installments,
        'installment_amount': installment_amount
    })

@csrf_exempt
def pos_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = data.get('amount')
            if not amount or amount <= 0:
                return JsonResponse({'success': False, 'error': 'مبلغ نامعتبر'}, status=400)

            import random
            import string
            transaction_id = ''.join(random.choices(string.digits, k=12))
            card_number = ''.join(random.choices(string.digits, k=16))

            return JsonResponse({
                'success': True,
                'amount': amount,
                'transaction_id': transaction_id,
                'card_number': card_number
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'روش نادرست'}, status=405)
import json
from decimal import Decimal, ROUND_HALF_UP

import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction

from cart.models import Cart
from orders.models import Order


def _amount_in_paise(order):
    return int((order.get_total_cost() * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise RuntimeError('Razorpay credentials are not configured.')
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def _payment_failure(request, message, status=503):
    return render(request, 'payment/failed.html', {'message': message}, status=status)


@login_required
def payment_start_view(request):
    order_id = request.session.get('pending_order_id')
    if not order_id:
        messages.info(request, 'There is no pending payment.')
        return redirect('cart')
    return redirect('payment:create', order_id=order_id)


@login_required
def create_razorpay_order_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.payment_status == 'paid' or order.paid:
        return redirect('order_confirmation', order_id=order.id)
    if order.payment_status not in ('pending', 'failed'):
        return _payment_failure(request, 'This order is not available for payment.', status=400)

    try:
        client = _razorpay_client()
        if not order.razorpay_order_id or order.payment_status == 'failed':
            razorpay_order = client.order.create(data={
                'amount': _amount_in_paise(order),
                'currency': 'INR',
                'receipt': f'order_{order.id}',
                'notes': {'django_order_id': str(order.id)},
            })
            order.razorpay_order_id = razorpay_order['id']
            order.payment_status = 'pending'
            order.save(update_fields=['razorpay_order_id', 'payment_status', 'updated_at'])
    except Exception:
        return _payment_failure(request, 'Payment service is temporarily unavailable. Your order is still pending.')

    context = {
        'order': order,
        'amount_paise': _amount_in_paise(order),
        'payment_config': {
            'key': settings.RAZORPAY_KEY_ID,
            'amount': _amount_in_paise(order),
            'orderId': order.id,
            'razorpayOrderId': order.razorpay_order_id,
            'verifyUrl': f'/payment/verify/{order.id}/',
        },
    }
    return render(request, 'payment/checkout.html', context)


@login_required
@require_POST
def verify_payment_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    payload = request.POST
    razorpay_order_id = payload.get('razorpay_order_id', '').strip()
    razorpay_payment_id = payload.get('razorpay_payment_id', '').strip()
    razorpay_signature = payload.get('razorpay_signature', '').strip()

    if order.payment_status == 'paid' or order.paid:
        if razorpay_payment_id and razorpay_payment_id == order.razorpay_payment_id:
            return JsonResponse({'status': 'already_paid', 'redirect_url': f'/orders/confirmation/{order.id}/'})
        return JsonResponse({'error': 'Order is already paid.'}, status=400)

    if not all((razorpay_order_id, razorpay_payment_id, razorpay_signature)):
        order.payment_status = 'failed'
        order.save(update_fields=['payment_status', 'updated_at'])
        return JsonResponse({'error': 'Missing Razorpay payment details.'}, status=400)

    if not order.razorpay_order_id or razorpay_order_id != order.razorpay_order_id:
        return JsonResponse({'error': 'Invalid Razorpay order.'}, status=400)

    try:
        client = _razorpay_client()
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except Exception:
        order.payment_status = 'failed'
        order.save(update_fields=['payment_status', 'updated_at'])
        return JsonResponse({'error': 'Payment verification failed.'}, status=400)

    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order.id, user=request.user)
        if order.payment_status != 'paid':
            order.payment_status = 'paid'
            order.paid = True
            order.status = 'Processing'
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.save(update_fields=[
                'payment_status', 'paid', 'status', 'razorpay_payment_id',
                'razorpay_signature', 'updated_at',
            ])
            # Decrement inventory
            for item in order.items.select_related('product'):
                if item.product.stock is not None:
                    item.product.stock = max(0, item.product.stock - item.quantity)
                    item.product.save(update_fields=['stock'])

            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart.items.all().delete()

    if request.session.get('pending_order_id') == order.id:
        del request.session['pending_order_id']
    return JsonResponse({'status': 'paid', 'redirect_url': f'/orders/confirmation/{order.id}/'})


@csrf_exempt
@require_POST
def webhook_view(request):
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        return JsonResponse({'error': 'Webhook is not configured.'}, status=503)
    signature = request.headers.get('X-Razorpay-Signature', '')
    try:
        client = _razorpay_client()
        client.utility.verify_webhook_signature(
            request.body.decode('utf-8'), signature, settings.RAZORPAY_WEBHOOK_SECRET,
        )
        event = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid webhook.'}, status=400)

    if event.get('event') not in ('payment.captured', 'order.paid'):
        return JsonResponse({'status': 'ignored'})

    payload = event.get('payload', {})
    payment_entity = payload.get('payment', {}).get('entity', {})
    order_entity = payload.get('order', {}).get('entity', {})
    razorpay_order_id = payment_entity.get('order_id') or order_entity.get('id')
    order = Order.objects.filter(razorpay_order_id=razorpay_order_id).first()
    if not order:
        return JsonResponse({'error': 'Order not found.'}, status=404)
    if order.payment_status == 'paid':
        return JsonResponse({'status': 'already_paid'})

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        order.payment_status = 'paid'
        order.paid = True
        order.status = 'Processing'
        if payment_entity.get('id'):
            order.razorpay_payment_id = payment_entity['id']
        order.save(update_fields=['payment_status', 'paid', 'status', 'razorpay_payment_id', 'updated_at'])

        # Decrement inventory
        for item in order.items.select_related('product'):
            if item.product.stock is not None:
                item.product.stock = max(0, item.product.stock - item.quantity)
                item.product.save(update_fields=['stock'])

        if order.user:
            cart = Cart.objects.filter(user=order.user).first()
            if cart:
                cart.items.all().delete()
    return JsonResponse({'status': 'paid'})
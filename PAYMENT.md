# Razorpay Payment Integration

## Configuration

Set these environment variables for local Razorpay Test Mode:

```text
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

Create Test Mode credentials in the Razorpay Dashboard under **Account & Settings > API Keys**. Never commit these values or expose `RAZORPAY_KEY_SECRET` in browser code.

Run the normal Django setup and migrations:

```text
python manage.py migrate
python manage.py runserver
```

## Flow

Checkout creates a pending Django order and snapshots the cart item prices. The server calculates the total and creates a Razorpay order in INR paise. Razorpay Checkout receives only the public key ID and server-created Razorpay order ID.

The browser sends the three Razorpay response values to the authenticated Django verification endpoint. The server checks order ownership, matches the Razorpay order ID, and verifies the signature with the secret key. Only then does it set `payment_status=paid`, set the legacy `paid` flag, clear the user's cart, and show confirmation.

Cancelled, failed, missing, invalid, or duplicate requests do not create another order or clear the cart. Verification is idempotent for the same successful payment.

## Webhooks

The endpoint is `/payment/webhook/`. In the Razorpay Dashboard, create a webhook pointing to this HTTPS URL, subscribe to `payment.captured` (and `order.paid` if used), and use the generated webhook secret as `RAZORPAY_WEBHOOK_SECRET`.

The endpoint verifies `X-Razorpay-Signature` before processing events and ignores unsupported events. Localhost cannot receive Razorpay webhooks directly without a secure tunnel or deployed HTTPS endpoint.

## Local testing limitations

Automated tests mock all Razorpay SDK calls and never contact Razorpay. A complete browser payment requires valid Razorpay Test Mode credentials, internet access to Razorpay Checkout, and a test payment method. Without credentials, the application leaves orders pending and reports that payment service configuration is unavailable.
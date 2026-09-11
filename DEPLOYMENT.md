# Deployment configuration

Set these values in the deployment environment before starting Django. Do not commit production secrets or a production `.env` file.

```text
SECRET_KEY=<strong unique randomly generated value>
DEBUG=False
ALLOWED_HOSTS=shop.example.com,www.shop.example.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<smtp username>
EMAIL_HOST_PASSWORD=<smtp password>
DEFAULT_FROM_EMAIL=webmaster@example.com
```

`SECRET_KEY` is required. The application fails during startup when it is missing rather than using an insecure fallback. Run `python manage.py collectstatic --noinput` during deployment so WhiteNoise can serve the hashed static files.

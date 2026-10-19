import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)


class ZarinpalError(Exception):
    """Raised when Zarinpal refuses a request or cannot be reached."""


def _api_base(sandbox):
    if sandbox:
        return "https://sandbox.zarinpal.com"
    return "https://payment.zarinpal.com"


def _post_json(url, payload):
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read()
    except HTTPError as exc:
        logger.warning("Zarinpal API returned HTTP %s", exc.code)
        raise ZarinpalError("ارتباط با درگاه پرداخت برقرار نشد.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        logger.warning("Zarinpal API request failed: %s", exc)
        raise ZarinpalError("در حال حاضر ارتباط با درگاه پرداخت ممکن نیست.") from exc

    try:
        result = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.error("Zarinpal API returned invalid JSON")
        raise ZarinpalError("پاسخ درگاه پرداخت قابل خواندن نیست.") from exc

    if not isinstance(result, dict):
        logger.error("Zarinpal API returned an unexpected response type")
        raise ZarinpalError("پاسخ درگاه پرداخت معتبر نیست.")
    return result


def create_payment(merchant_id, amount_rial, callback_url, description, email="", mobile="",
                   sandbox=True):
    result = _post_json(
        f"{_api_base(sandbox)}/pg/v4/payment/request.json",
        {
            "merchant_id": merchant_id,
            "amount": amount_rial,
            "callback_url": callback_url,
            "description": description[:255],
            "metadata": {"email": email, "mobile": mobile},
        },
    )
    data = result.get("data") or {}
    if data.get("code") != 100 or not data.get("authority"):
        logger.warning("Zarinpal payment request rejected: %s", result.get("errors"))
        raise ZarinpalError("درخواست پرداخت از سوی درگاه پذیرفته نشد.")
    return {
        "authority": str(data["authority"]),
        "payment_url": f"{_api_base(sandbox)}/pg/StartPay/{data['authority']}",
    }


def verify_payment(merchant_id, amount_rial, authority, sandbox=True):
    result = _post_json(
        f"{_api_base(sandbox)}/pg/v4/payment/verify.json",
        {
            "merchant_id": merchant_id,
            "amount": amount_rial,
            "authority": authority,
        },
    )
    data = result.get("data") or {}
    if data.get("code") not in (100, 101):
        logger.warning("Zarinpal payment verification rejected: %s", result.get("errors"))
        raise ZarinpalError("پرداخت توسط درگاه تأیید نشد.")
    return {
        "ref_id": str(data.get("ref_id", "")),
        "already_verified": data.get("code") == 101,
    }

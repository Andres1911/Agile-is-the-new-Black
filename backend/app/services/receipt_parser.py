import io
import re
from datetime import datetime

from PIL import Image

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

try:
    import pytesseract
except ImportError:
    pytesseract = None


SUPPORTED_EXTENSIONS = {"jpg", "jpeg", "png", "heic", "heif"}

DATE_PATTERNS = [
    r"(\d{4}[-/]\d{2}[-/]\d{2})",
    r"(\d{2}[-/]\d{2}[-/]\d{4})",
    r"(\d{2}[-/]\d{2}[-/]\d{2})",
    r"([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",
]

TOTAL_PATTERNS = [
    r"(?:total|amount\s*due|balance\s*due|grand\s*total)\s*[:\s]*\$?\s*([\d]+[.,]\d{2})",
    r"(?:total)\s*\$?\s*([\d]+[.,]\d{2})",
    r"\$\s*([\d]+[.,]\d{2})\s*$",
]

ITEM_PATTERN = re.compile(r"^(.+?)\s+\$?\s*([\d]+[.,]\d{2})\s*$", re.MULTILINE)

SKIP_KEYWORDS = {
    "total",
    "subtotal",
    "sub-total",
    "tax",
    "tip",
    "change",
    "cash",
    "credit",
    "debit",
    "visa",
    "mastercard",
    "amex",
    "balance",
    "amount due",
    "grand total",
    "discount",
    "savings",
    "hst",
    "gst",
    "pst",
}


def detect_format_from_bytes(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(data) >= 12:
        if data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"mif1"):
            return "heic"
    return None


def validate_file_extension(filename: str) -> str | None:
    if not filename or "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return None
    return ext


def extract_text_from_image(image_bytes: bytes) -> str:
    if pytesseract is None:
        raise RuntimeError("pytesseract is not installed")
    image = Image.open(io.BytesIO(image_bytes))
    if image.mode != "RGB":
        image = image.convert("RGB")
    text = pytesseract.image_to_string(image)
    return text


def parse_date(text: str) -> str | None:
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            raw = match.group(1)
            for fmt in (
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%m/%d/%Y",
                "%m-%d-%Y",
                "%m/%d/%y",
                "%m-%d-%y",
                "%B %d, %Y",
                "%B %d %Y",
                "%b %d, %Y",
                "%b %d %Y",
            ):
                try:
                    dt = datetime.strptime(
                        raw.replace(",", ", ")
                        if "," not in raw and any(c.isalpha() for c in raw)
                        else raw,
                        fmt,
                    )
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return raw
    return None


def parse_total(text: str) -> float | None:
    lower = text.lower()
    for pattern in TOTAL_PATTERNS:
        matches = re.findall(pattern, lower)
        if matches:
            val = matches[-1].replace(",", ".")
            try:
                return float(val)
            except ValueError:
                continue
    return None


def parse_items(text: str) -> list[dict]:
    items = []
    for match in ITEM_PATTERN.finditer(text):
        name = match.group(1).strip()
        price_str = match.group(2).replace(",", ".")
        if any(kw in name.lower() for kw in SKIP_KEYWORDS):
            continue
        if len(name) < 2 or len(name) > 60:
            continue
        try:
            price = float(price_str)
        except ValueError:
            continue
        if price <= 0 or price > 10000:
            continue
        items.append({"item": name, "amount": round(price, 2)})
    return items


def parse_receipt(image_bytes: bytes) -> dict:
    text = extract_text_from_image(image_bytes)
    if not text or len(text.strip()) < 5:
        return {"success": False, "error": "no_receipt"}

    date = parse_date(text)
    total = parse_total(text)
    items = parse_items(text)

    if total is None and not items:
        return {"success": False, "error": "no_receipt"}

    if total is None and items:
        total = round(sum(i["amount"] for i in items), 2)

    warnings = []
    if date is None:
        warnings.append("date")
    if not items:
        warnings.append("items")

    partial = len(warnings) > 0

    return {
        "success": True,
        "partial": partial,
        "date": date,
        "totalAmount": total,
        "items": items,
        "warnings": warnings,
    }

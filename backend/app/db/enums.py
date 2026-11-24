import enum


class UserRole(str, enum.Enum):
    TENANT = "tenant"
    REALTOR = "realtor"
    ADMIN = "admin"


class RentType(str, enum.Enum):
    LONG_TERM = "long_term"
    DAILY = "daily"


class RoomsFilter(str, enum.Enum):
    STUDIO = "studio"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR_PLUS = "4+"


class PropertyStatus(str, enum.Enum):
    DRAFT = "draft"
    MODERATION = "moderation"
    ACTIVE = "active"
    NEEDS_FIX = "needs_fix"
    HIDDEN = "hidden"
    BLOCKED = "blocked"
    ARCHIVED = "archived"


class AvailabilityKind(str, enum.Enum):
    BOOKED = "booked"
    BLOCKED = "blocked"


class InquiryStatus(str, enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    AWAITING_CONFIRMATIONS = "awaiting_confirmations"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ContactChannel(str, enum.Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    PHONE = "phone"


class DealStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"


class ConfirmationSide(str, enum.Enum):
    REALTOR = "realtor"
    CLIENT = "client"
    ADMIN = "admin"


class ConfirmationDecision(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewStatus(str, enum.Enum):
    PENDING_MODERATION = "pending_moderation"
    PUBLISHED = "published"
    REJECTED = "rejected"
    HIDDEN = "hidden"


class LongTermAvailability(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    UNKNOWN = "unknown"


# Exact amenity keys matching TZ Russian labels mapping
AMENITY_KEYS = (
    "wifi",
    "air_conditioning",
    "kitchen",
    "oven",
    "microwave",
    "parking",
    "furniture",
    "dishwasher",
    "sea_view",
    "bedrooms_with_windows",
    "washing_machine",
    "balcony",
    "elevator",
    "central_heating",
    "hot_water",
    "pets_allowed",
    "tv",
    "mountain_view",
)

AMENITY_LABELS_RU = {
    "wifi": "Wi‑Fi",
    "air_conditioning": "кондиционер",
    "kitchen": "кухня",
    "oven": "духовка",
    "microwave": "микроволновка",
    "parking": "парковка",
    "furniture": "мебель",
    "dishwasher": "посудомоечная машина",
    "sea_view": "вид на море",
    "bedrooms_with_windows": "Спальни с окнами",
    "washing_machine": "стиральная машина",
    "balcony": "балкон",
    "elevator": "лифт",
    "central_heating": "центральное отопление",
    "hot_water": "горячая вода",
    "pets_allowed": "можно с животными",
    "tv": "телевизор",
    "mountain_view": "вид на горы",
}

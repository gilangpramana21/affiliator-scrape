"""Data validation for affiliator data"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.models.models import AffiliatorData

logger = logging.getLogger(__name__)

# Indonesian phone number regex: starts with 08 or +62, followed by 8-13 digits
PHONE_REGEX = re.compile(r"^(08|\+62)\d{8,13}$")

# Field constraints
USERNAME_MAX_LEN = 100
PERCENTAGE_MIN = 0.0
PERCENTAGE_MAX = 100.0

NUMERIC_INT_FIELDS = {"pengikut", "produk_terjual", "rata_rata_tayangan"}
NUMERIC_FLOAT_FIELDS = {
    "gmv",
    "tingkat_interaksi",
    "gmv_per_pembeli",
    "gmv_harian",
    "gmv_mingguan",
    "gmv_bulanan",
}


@dataclass
class FieldValidation:
    """Result of validating a single field"""
    is_valid: bool
    error: Optional[str]
    value: Any


@dataclass
class ValidationResult:
    """Result of validating an AffiliatorData object"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    field_errors: Dict[str, str] = field(default_factory=dict)


class DataValidator:
    """Validates extracted affiliator data against business rules"""

    def validate(self, data: AffiliatorData) -> ValidationResult:
        """Validate all fields of an AffiliatorData instance.

        Returns a ValidationResult indicating overall validity and any
        per-field errors encountered.
        """
        errors: List[str] = []
        field_errors: Dict[str, str] = {}

        fields_to_check = {
            "username": data.username,
            "kategori": data.kategori,
            "pengikut": data.pengikut,
            "gmv": data.gmv,
            "produk_terjual": data.produk_terjual,
            "rata_rata_tayangan": data.rata_rata_tayangan,
            "tingkat_interaksi": data.tingkat_interaksi,
            "gmv_per_pembeli": data.gmv_per_pembeli,
            "gmv_harian": data.gmv_harian,
            "gmv_mingguan": data.gmv_mingguan,
            "gmv_bulanan": data.gmv_bulanan,
        }

        for fname, fvalue in fields_to_check.items():
            result = self.validate_field(fname, fvalue)
            if not result.is_valid:
                field_errors[fname] = result.error
                errors.append(f"{fname}: {result.error}")
                logger.error("Validation error for field '%s': %s", fname, result.error)

        # nomor_kontak is optional — only validate if present
        if data.nomor_kontak is not None:
            result = self.validate_field("nomor_kontak", data.nomor_kontak)
            if not result.is_valid:
                field_errors["nomor_kontak"] = result.error
                errors.append(f"nomor_kontak: {result.error}")
                logger.error("Validation error for field 'nomor_kontak': %s", result.error)
        if data.nomor_whatsapp is not None:
            result = self.validate_field("nomor_whatsapp", data.nomor_whatsapp)
            if not result.is_valid:
                field_errors["nomor_whatsapp"] = result.error
                errors.append(f"nomor_whatsapp: {result.error}")
                logger.error("Validation error for field 'nomor_whatsapp': %s", result.error)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            field_errors=field_errors,
        )

    def validate_field(self, field_name: str, value: Any) -> FieldValidation:
        """Validate a single field by name.

        Dispatches to the appropriate validation rule based on field_name.
        Returns a FieldValidation with the (possibly converted) value.
        """
        if field_name == "username":
            return self._validate_username(value)
        if field_name == "kategori":
            return self._validate_non_empty_string(field_name, value)
        if field_name in NUMERIC_INT_FIELDS:
            return self._validate_non_negative_int(field_name, value)
        if field_name == "gmv":
            return self._validate_non_negative_number(field_name, value)
        if field_name == "tingkat_interaksi":
            return self._validate_percentage(value)
        if field_name == "nomor_kontak":
            return self._validate_phone(value)
        if field_name == "nomor_whatsapp":
            return self._validate_phone(value)
        if field_name in {"gmv", "gmv_per_pembeli", "gmv_harian", "gmv_mingguan", "gmv_bulanan"}:
            return self._validate_non_negative_number(field_name, value)

        # Unknown field — pass through without validation
        return FieldValidation(is_valid=True, error=None, value=value)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_username(self, value: Any) -> FieldValidation:
        if not isinstance(value, str) or not value.strip():
            msg = "username must be a non-empty string"
            return FieldValidation(is_valid=False, error=msg, value=value)
        if len(value) > USERNAME_MAX_LEN:
            msg = f"username must not exceed {USERNAME_MAX_LEN} characters"
            return FieldValidation(is_valid=False, error=msg, value=value)
        return FieldValidation(is_valid=True, error=None, value=value)

    def _validate_non_empty_string(self, field_name: str, value: Any) -> FieldValidation:
        if not isinstance(value, str) or not value.strip():
            msg = f"{field_name} must be a non-empty string"
            return FieldValidation(is_valid=False, error=msg, value=value)
        return FieldValidation(is_valid=True, error=None, value=value)

    def _validate_non_negative_int(self, field_name: str, value: Any) -> FieldValidation:
        try:
            converted = int(value)
        except (TypeError, ValueError):
            msg = f"{field_name} must be a numeric value"
            return FieldValidation(is_valid=False, error=msg, value=value)
        if converted < 0:
            msg = f"{field_name} must be a non-negative integer"
            return FieldValidation(is_valid=False, error=msg, value=value)
        return FieldValidation(is_valid=True, error=None, value=converted)

    def _validate_non_negative_number(self, field_name: str, value: Any) -> FieldValidation:
        try:
            converted = float(value)
        except (TypeError, ValueError):
            msg = f"{field_name} must be a numeric value"
            return FieldValidation(is_valid=False, error=msg, value=value)
        if converted < 0:
            msg = f"{field_name} must be a non-negative number"
            return FieldValidation(is_valid=False, error=msg, value=value)
        return FieldValidation(is_valid=True, error=None, value=converted)

    def _validate_percentage(self, value: Any) -> FieldValidation:
        try:
            converted = float(value)
        except (TypeError, ValueError):
            msg = "tingkat_interaksi must be a numeric value"
            return FieldValidation(is_valid=False, error=msg, value=value)
        if not (PERCENTAGE_MIN <= converted <= PERCENTAGE_MAX):
            msg = f"tingkat_interaksi must be between {PERCENTAGE_MIN} and {PERCENTAGE_MAX}"
            return FieldValidation(is_valid=False, error=msg, value=value)
        return FieldValidation(is_valid=True, error=None, value=converted)

    def _validate_phone(self, value: Any) -> FieldValidation:
        if not isinstance(value, str):
            msg = "nomor_kontak must be a string"
            return FieldValidation(is_valid=False, error=msg, value=value)
        if not PHONE_REGEX.match(value):
            msg = "nomor_kontak must be a valid Indonesian phone number (08... or +62...)"
            return FieldValidation(is_valid=False, error=msg, value=value)
        return FieldValidation(is_valid=True, error=None, value=value)

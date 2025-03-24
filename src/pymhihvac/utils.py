"""Utility functions for the MHI HVAC integration."""

import asyncio
from collections import Counter
from collections.abc import Collection, Iterable
import logging
import re
from socket import gaierror
from typing import Any

import voluptuous as vol

_LOGGER = logging.getLogger(__name__)


class InvalidTemperatureException(Exception):
    """Custom exception raised when an invalid temperature value is encountered.

    This exception is raised if the temperature value cannot be converted to a float,
    or if it falls outside the acceptable range.
    """


def format_exception(e: Exception) -> str:
    """Format an exception into a string.

    :param e: The exception to format.
    :return: The formatted exception string.
    """
    return re.sub(r"\s+", " ", f"{type(e).__name__}{f': {e}' if f'{e}' else ''}")


def validate_temperature(value: Any) -> str:
    """Validate a temperature value.

    :param value: The temperature value to validate.
    :return: The validated temperature value as a string.
    :raises InvalidTemperatureException: If the value is not a float or is out of range.
    """
    min_temp = 18.0
    max_temp = 30.0

    try:
        float_value = float(value)
    except (ValueError, TypeError) as e:
        raise InvalidTemperatureException(
            f"Value '{value}' cannot be converted to a float."
        ) from e

    if not (min_temp <= float_value <= max_temp):
        raise InvalidTemperatureException(
            f"Value '{float_value}' is out of range [{min_temp}, {max_temp}]."
        )

    return str(float_value)


def build_payload(
    property_spec: str | Iterable[str],
    value: Any,
    property_mappings: dict[str, tuple[str, dict[Any, Any] | None]],
    logger: logging.Logger,
) -> dict[str, Any] | None:
    """Build a payload dictionary using property_mappings.

    :param property_spec: A single property (str) or an iterable (tuple/list) of properties.
    :param value: A single value or an iterable of values matching property_spec.
    :param property_mappings: Dictionary mapping HA property names to a tuple of (API property, mapping dict).
    :param logger: Logger for error messages.
    :return: A dictionary mapping API properties to values or None on error.
    """
    payload: dict[str, Any] = {}
    if isinstance(property_spec, str):
        mapping_tuple = property_mappings.get(property_spec)
        if mapping_tuple is None:
            logger.error("Unsupported property: %s", property_spec)
            return None
        api_prop, mapping = mapping_tuple
        api_value = mapping.get(value) if mapping else str(value)
        if mapping and api_value is None:
            logger.error("Unsupported value for %s: %s", property_spec, value)
            return None
        payload = {api_prop: api_value}
    elif isinstance(property_spec, (tuple, list)):
        if not isinstance(value, (tuple, list)) or len(property_spec) != len(value):
            logger.error(
                "For composite properties, value must be an iterable with the same length as property_spec"
            )
            return None
        for key, val in zip(property_spec, value, strict=False):
            mapping_tuple = property_mappings.get(key)
            if mapping_tuple is None:
                logger.error("Unsupported property: %s", key)
                return None
            api_prop, mapping = mapping_tuple
            api_value = mapping.get(val) if mapping else str(val)
            if mapping and api_value is None:
                logger.error("Unsupported value for %s: %s", key, val)
                return None
            payload[api_prop] = api_value
    else:
        logger.error("property_spec must be a string or a tuple/list of strings")
        return None

    return payload


def validate_properties(props: dict, validators: dict) -> dict:
    """Validate a dictionary of properties against a schema.

    :param props: The dictionary of properties to validate.
    :param validators: The voluptuous schema to validate against.
    :return: The validated dictionary of properties.
    :raises ValueError: If the properties are invalid.
    """
    properties_schema = vol.Schema(validators, extra=vol.PREVENT_EXTRA)
    try:
        return properties_schema(props)
    except (vol.MultipleInvalid, InvalidTemperatureException) as e:
        _LOGGER.error("Invalid properties: %s", format_exception(e))
        raise ValueError from e


def find_most_frequent(data: Collection[Any]) -> Any:
    """Find the most frequent item in a collection.

    :param data: A collection of items.
    :return: The most frequent item, or None if the collection is empty.
    """
    return Counter(data).most_common(1)[0][0] if data else None


def calculate_average(
    values: list[Any],
    precision: int | None = 1,
) -> float | None:
    """Calculate the average of a list of values, handling non-numeric types and None.

    :param values: A list of values to average. Non-numeric values are ignored.
    :param precision: Number of decimal places to round to, or None for no rounding.
    :return: The average of the numeric values in the list, rounded to the specified precision, or None if the list is empty or contains only None and/or non-numeric values.
    """
    cleaned = []
    for val in values:
        if val is None:
            continue
        if not isinstance(val, (int, float)):
            return None  # Now reachable because list might contain non-numbers
        cleaned.append(float(val))

    if not cleaned:
        return None

    avg = sum(cleaned) / len(cleaned)
    return round(avg, precision) if precision is not None else avg


async def async_resolve_hostname(hostname: str) -> str:
    """Resolve a hostname to an IP address asynchronously.

    :param hostname: The hostname to resolve.
    :return: The resolved IP address, or "0.0.0.0" if resolution fails.
    """
    try:
        loop = asyncio.get_running_loop()
        addr_info = await loop.getaddrinfo(hostname, None)
        # getaddrinfo returns a list; take the first tuple and then index 4[0] for the IP.
        return addr_info[0][4][0]
    except (gaierror, TimeoutError):
        # Handle DNS resolution error
        return "0.0.0.0"


def raise_vol_invalid(message: str, e: Exception | None = None) -> None:
    """Raise a voluptuous.Invalid exception with an optional nested exception.

    :param message: The error message.
    :param e: An optional nested exception.
    :raises vol.Invalid: Always raises this exception.
    """
    if e is not None:
        raise vol.Invalid(f"{message} {format_exception(e)}") from e
    raise vol.Invalid(message)

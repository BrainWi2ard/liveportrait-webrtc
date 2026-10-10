"""
sdp_normalizer.py
Sanitizes and normalizes WebRTC SDP descriptions and ICE candidates
to prevent network-layer correlation and device fingerprinting.
"""

import re
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Regex patterns for private IP ranges
PRIVATE_IPV4_PATTERN = r'\b(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|127\.0\.0\.1|169\.254\.\d{1,3}\.\d{1,3})\b'
PRIVATE_IPV6_PATTERN = r'(fe80::|::1|fc00::|fd00::)'

# Proprietary codec signatures to strip
PROPRIETARY_ATTRIBUTES = [
    "x-google-flag",
    "x-google-max-bitrate",
    "x-google-min-bitrate",
    "x-google-start-bitrate",
    "x-gstnv",
    "x-ulpfec",
]


def mask_private_ip(ip_address: str) -> str:
    """
    Mask private IP addresses with generic relay tokens.

    Args:
        ip_address: IP address to mask

    Returns:
        Masked IP address (0.0.0.0 for IPv4, :: for IPv6)
    """
    if re.match(PRIVATE_IPV6_PATTERN, ip_address):
        return "::"
    return "0.0.0.0"


def normalize_sdp_offer(sdp_content: str) -> str:
    """
    Strips hardware-specific codec preferences, normalizes crypto attributes,
    and removes local IP address disclosures from SDP strings.

    Args:
        sdp_content: Raw SDP offer string

    Returns:
        Sanitized SDP offer string
    """
    lines = sdp_content.split("\n")
    sanitized_lines: List[str] = []

    for line in lines:
        line = line.rstrip()

        # Mask private IP disclosures in candidate lines
        if line.startswith("a=candidate:"):
            # Replace private IPv4 addresses
            line = re.sub(PRIVATE_IPV4_PATTERN, "0.0.0.0", line)
            # Replace private IPv6 addresses
            line = re.sub(PRIVATE_IPV6_PATTERN, "::", line)
            # Strip host candidate type to reduce fingerprintability
            if "typ host" in line:
                logger.debug("Normalizing host candidate to relay equivalent")
                line = line.replace("typ host", "typ relay")

        # Strip proprietary hardware profile signatures
        skip_line = False
        for attr in PROPRIETARY_ATTRIBUTES:
            if attr in line:
                logger.debug(f"Stripping proprietary attribute: {attr}")
                skip_line = True
                break

        if skip_line:
            continue

        # Normalize DTLS-SRTP fingerprint attributes (remove specific cipher info)
        if line.startswith("a=fingerprint:"):
            # Keep fingerprint but normalize the hash algorithm
            line = re.sub(r"fingerprint:(sha-\d+)", "fingerprint:sha-256", line)

        # Remove ice-ufrag/ice-pwd (can leak session timing info)
        # Note: This is aggressive; in production, consider keeping but randomizing
        if line.startswith(("a=ice-ufrag:", "a=ice-pwd:")):
            logger.debug("Normalizing ICE credentials")
            parts = line.split(":")
            if len(parts) == 2:
                # Replace with generic placeholder
                prefix = parts[0]
                line = f"{prefix}:***"

        sanitized_lines.append(line)

    return "\r\n".join(sanitized_lines)


def normalize_sdp_answer(sdp_content: str) -> str:
    """
    Normalize SDP answer (similar to offer normalization).

    Args:
        sdp_content: Raw SDP answer string

    Returns:
        Sanitized SDP answer string
    """
    return normalize_sdp_offer(sdp_content)


def sanitize_ice_candidate(candidate_str: str) -> Optional[str]:
    """
    Sanitize individual ICE candidate string.
    Returns None if candidate should be filtered out entirely.

    Args:
        candidate_str: Raw ICE candidate string

    Returns:
        Sanitized candidate string, or None if filtered
    """
    if not candidate_str:
        return None

    # Filter out host candidates (expose local IPs)
    if "typ host" in candidate_str:
        logger.debug("Filtering host candidate to prevent local IP disclosure")
        return None

    # Filter out src address disclosures
    if "raddr" in candidate_str or "rport" in candidate_str:
        logger.debug("Filtering reflexive candidate metadata")
        candidate_str = re.sub(r" raddr \d+\.\d+\.\d+\.\d+ ", " ", candidate_str)
        candidate_str = re.sub(r" rport \d+ ", " ", candidate_str)

    # Mask any remaining private IPs
    candidate_str = re.sub(PRIVATE_IPV4_PATTERN, "0.0.0.0", candidate_str)
    candidate_str = re.sub(PRIVATE_IPV6_PATTERN, "::", candidate_str)

    return candidate_str

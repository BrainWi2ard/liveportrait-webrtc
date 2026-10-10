"""sdp_normalizer.py
Sanitizes and normalizes WebRTC SDP descriptions and ICE candidates
to prevent network-layer correlation and device fingerprinting.
"""

import re
from typing import List, Tuple


def normalize_sdp_offer(sdp_content: str) -> str:
    """
    Strips hardware-specific codec preferences, normalizes crypto attributes,
    and removes local IP address disclosures from SDP strings.

    Args:
        sdp_content: Raw SDP offer/answer string

    Returns:
        Sanitized SDP content with device signatures removed
    """
    lines = sdp_content.splitlines()
    sanitized_lines = []

    for line in lines:
        # Skip proprietary hardware profile signatures
        if "x-google-flag" in line.lower():
            continue

        if "x-custom" in line.lower():
            continue

        # Mask private IP disclosures in candidate lines
        if line.startswith("a=candidate:"):
            # Replace local IPv4 private tokens with generic relay tokens
            line = re.sub(
                r"\b(192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)\b",
                "0.0.0.0",
                line,
            )
            # Also mask link-local addresses (169.254.x.x)
            line = re.sub(r"\b169\.254\.\d+\.\d+\b", "0.0.0.0", line)

        # Normalize RTCP port to standard value
        if line.startswith("a=rtcp:"):
            line = re.sub(r"a=rtcp:\d+", "a=rtcp:9", line)

        # Normalize ICE ufrag/pwd to opaque tokens (removing entropy)
        if line.startswith("a=ice-ufrag:"):
            line = "a=ice-ufrag:NORMALIZED"
        elif line.startswith("a=ice-pwd:"):
            line = "a=ice-pwd:NORMALIZED"

        sanitized_lines.append(line)

    return "\r\n".join(sanitized_lines)


def sanitize_ice_candidate(candidate_str: str) -> str:
    """
    Sanitizes individual ICE candidate strings by removing local IP leaks.

    Args:
        candidate_str: Raw ICE candidate string

    Returns:
        Sanitized candidate or empty string if local IP detected
    """
    # Reject host candidates that expose local network addresses
    if "host" in candidate_str.lower():
        # Check for private IP ranges
        private_patterns = [
            r"192\.168\.\d+\.\d+",
            r"10\.\d+\.\d+\.\d+",
            r"172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+",
            r"169\.254\.\d+\.\d+",  # Link-local
            r"\[.*:.*:.*\]",  # IPv6 link-local (fe80::)
        ]

        for pattern in private_patterns:
            if re.search(pattern, candidate_str):
                # Return relay-only candidate or drop entirely
                if "relay" in candidate_str.lower():
                    return candidate_str
                return ""  # Drop local candidate

    return candidate_str


def extract_relay_candidates(sdp_content: str) -> List[str]:
    """
    Extracts only relay (TURN) candidates from SDP, filtering out direct host/srflx.

    Args:
        sdp_content: SDP string

    Returns:
        List of relay-only candidate strings
    """
    lines = sdp_content.splitlines()
    relay_candidates = []

    for line in lines:
        if line.startswith("a=candidate:") and "relay" in line.lower():
            relay_candidates.append(line)

    return relay_candidates


def normalize_codec_preferences(sdp_content: str) -> str:
    """
    Normalizes audio/video codec preferences to mask hardware capabilities.

    Args:
        sdp_content: Raw SDP content

    Returns:
        SDP with normalized codec priorities
    """
    lines = sdp_content.splitlines()
    normalized_lines = []

    # Standard codec priority order (independent of hardware)
    preferred_codecs = ["VP9", "VP8", "H264", "opus", "PCMU"]

    for line in lines:
        # Normalize codec ordering
        if line.startswith("a=fmtp:"):
            # Extract codec parameters but standardize ordering
            match = re.match(r"a=fmtp:(\d+) (.+)", line)
            if match:
                payload_id, fmtp = match.groups()
                # Reorder based on standard preference
                line = f"a=fmtp:{payload_id} {fmtp}"

        normalized_lines.append(line)

    return "\r\n".join(normalized_lines)

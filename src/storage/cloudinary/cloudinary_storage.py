"""Cloudinary storage adapter for user media.

Public media (`avatar`, `topic_cover`, `post_cover`) is uploaded as
`resource_type=image` with delivery type `upload`; private evidence uses
`type=authenticated`, and PDFs additionally need `resource_type=raw`.

The browser uploads straight to Cloudinary with a short-lived signature minted
here. The signature is the only credential the browser ever sees: `api_secret`
never leaves the server, and every asset is re-read through the Admin API before
its metadata is trusted.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import cloudinary
import cloudinary.utils
from cloudinary import api, uploader
from cloudinary.exceptions import Error as CloudinaryError
from cloudinary.exceptions import NotFound as CloudinaryNotFound

logger = logging.getLogger(__name__)

PUBLIC_DELIVERY_TYPE = "upload"
PRIVATE_DELIVERY_TYPE = "authenticated"

# Cloudinary derives the format from the uploaded bytes, so the public id must
# not carry the extension the way an S3 object key does.
MIME_TO_FORMATS: dict[str, set[str]] = {
    "image/jpeg": {"jpg", "jpeg"},
    "image/png": {"png"},
    "image/webp": {"webp"},
    "application/pdf": {"pdf"},
}

RESOURCE_TYPE_BY_MIME: dict[str, str] = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "application/pdf": "raw",
}


def resource_type_for(mime_type: str, *, private: bool) -> str:
    """Pick the Cloudinary resource type; private PDFs must stay `raw`."""
    if private and mime_type == "application/pdf":
        return "raw"
    return RESOURCE_TYPE_BY_MIME.get(mime_type, "image")


class CloudinaryUploadStorage:
    provider = "cloudinary"
    # Signed direct uploads cannot express a byte ceiling the way a presigned
    # PUT can, so the declared size is enforced by the completion check instead.
    enforces_size_server_side = False

    def __init__(
        self,
        *,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        root_folder: str = "campusmeet",
    ) -> None:
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.root_folder = (root_folder or "campusmeet").strip("/")
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )

    # -- upload ticket ----------------------------------------------------

    def build_upload_ticket(
        self,
        *,
        public_id: str,
        resource_type: str,
        delivery_type: str,
        max_size: int,
        expires_in: int,
    ) -> dict[str, Any]:
        """Mint the signed fields the browser posts alongside the file."""
        timestamp = int(time.time())
        # Every signed value is a non-empty string on purpose: Cloudinary's
        # signature algorithm drops falsy entries, so a Python bool would be
        # signed as absent while still being sent as a form field.
        signed: dict[str, str] = {
            "public_id": public_id,
            "timestamp": str(timestamp),
            "type": delivery_type,
            "overwrite": "false",
        }
        signature = cloudinary.utils.api_sign_request(signed, self.api_secret)
        return {
            "provider": "cloudinary",
            "method": "POST",
            "encoding": "multipart/form-data",
            "url": (
                f"https://api.cloudinary.com/v1_1/{self.cloud_name}"
                f"/{resource_type}/upload"
            ),
            "file_field": "file",
            "max_size": max_size,
            "fields": {**signed, "signature": signature, "api_key": self.api_key},
        }

    def signature_of(self, fields: dict[str, Any]) -> str:
        """Recompute a signature for params the client echoed back."""
        return cloudinary.utils.api_sign_request(dict(fields), self.api_secret)

    def verify_echoed_signature(
        self, *, public_id: str, timestamp: Any, delivery_type: str, signature: str
    ) -> bool:
        """Confirm the client used exactly the ticket we issued."""
        if not signature:
            return False
        expected = self.signature_of(
            {
                "public_id": public_id,
                "timestamp": str(timestamp),
                "type": delivery_type,
                "overwrite": "false",
            }
        )
        return _constant_time_equals(expected, signature)

    # -- verification -----------------------------------------------------

    def fetch_asset(
        self, *, public_id: str, resource_type: str, delivery_type: str
    ) -> dict[str, Any] | None:
        """Read the asset back through the Admin API, the trusted source."""
        try:
            return api.resource(
                public_id,
                resource_type=resource_type,
                type=delivery_type,
            )
        except CloudinaryNotFound:
            return None
        except CloudinaryError:
            logger.warning(
                "Cloudinary Admin API lookup failed for resource_type=%s type=%s",
                resource_type,
                delivery_type,
            )
            return None

    def verified_asset(
        self, *, key: str, resource_type: str, delivery_type: str
    ) -> dict[str, Any] | None:
        """Return normalized metadata, or None when the asset cannot be trusted."""
        asset = self.fetch_asset(
            public_id=key, resource_type=resource_type, delivery_type=delivery_type
        )
        if asset is None:
            return None
        if str(asset.get("public_id") or "") != key:
            logger.warning("Cloudinary returned an unexpected public_id")
            return None
        if str(asset.get("resource_type") or "") != resource_type:
            return None
        if str(asset.get("type") or "") != delivery_type:
            return None
        version = asset.get("version")
        return {
            "asset_id": str(asset.get("asset_id") or ""),
            "public_id": key,
            "resource_type": resource_type,
            "delivery_type": delivery_type,
            "format": str(asset.get("format") or "").lower(),
            "bytes": int(asset.get("bytes") or 0),
            "version": int(version) if version is not None else 0,
            "url": self.public_url(
                public_id=key,
                resource_type=resource_type,
                delivery_type=delivery_type,
                format=str(asset.get("format") or "").lower(),
                version=int(version) if version is not None else None,
            ),
        }

    def public_url(
        self,
        *,
        public_id: str,
        resource_type: str,
        delivery_type: str,
        format: str,
        version: int | None = None,
    ) -> str:
        """Rebuild the delivery URL from trusted metadata, never from client input."""
        url, _ = cloudinary.utils.cloudinary_url(
            public_id,
            resource_type=resource_type,
            type=delivery_type,
            format=format or None,
            version=version,
            secure=True,
        )
        return url

    # -- delivery ---------------------------------------------------------

    def presign_download(
        self,
        *,
        key: str,
        resource_type: str,
        delivery_type: str,
        format: str,
        expires_in: int = 300,
    ) -> str:
        """Signed, short-lived download URL for private evidence."""
        import datetime

        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            seconds=expires_in
        )
        return cloudinary.utils.private_download_url(
            key,
            format,
            resource_type=resource_type,
            type=delivery_type,
            expires_at=int(expires_at.timestamp()),
        )

    # -- removal ----------------------------------------------------------

    def delete(
        self, *, key: str, resource_type: str = "image", delivery_type: str = "upload"
    ) -> bool:
        """Destroy an asset, purging CDN caches. Failures are logged, not raised."""
        try:
            result = uploader.destroy(
                key,
                resource_type=resource_type,
                type=delivery_type,
                invalidate=True,
            )
        except CloudinaryError:
            logger.warning(
                "Cloudinary destroy failed for resource_type=%s type=%s",
                resource_type,
                delivery_type,
            )
            return False
        return str((result or {}).get("result") or "") in {"ok", "not found"}


def _constant_time_equals(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left, right)

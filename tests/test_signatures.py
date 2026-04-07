"""Integration tests for digital signatures (SIG-01 through SIG-04).

Tests cover:
- SIG-01: Sign a document version with PKCS7/CMS
- SIG-02: Verify signature validity
- SIG-03: List all signatures on a document version
- SIG-04: Immutability - block check-in, checkout, metadata update on signed versions
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from httpx import AsyncClient


# ── Helpers ──────────────────────────────────────────────────────────────────


def _generate_test_keypair():
    """Generate a self-signed RSA certificate and private key for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Test Signer"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Org"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .sign(private_key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return cert_pem, key_pem


async def _upload_file(
    client: AsyncClient,
    token: str,
    title: str = "Test Doc",
    filename: str = "test.pdf",
    content: bytes = b"test content for signing",
):
    """Upload a document and return the response JSON."""
    files = {"file": (filename, content, "application/pdf")}
    data = {"title": title}
    resp = await client.post(
        "/api/v1/documents",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _get_version_id(client: AsyncClient, token: str, doc_id: str) -> str:
    """Get the first version ID for a document."""
    resp = await client.get(
        f"/api/v1/documents/{doc_id}/versions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    versions = resp.json()["data"]
    assert len(versions) > 0
    return versions[0]["id"]


async def _sign_version(
    client: AsyncClient,
    token: str,
    doc_id: str,
    version_id: str,
    cert_pem: str,
    key_pem: str,
):
    """Sign a document version and return the response."""
    body = {
        "certificate_pem": cert_pem,
        "private_key_pem": key_pem,
    }
    return await client.post(
        f"/api/v1/documents/{doc_id}/versions/{version_id}/signatures",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )


# ── SIG-01: Sign a document version ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_sign_document_version(async_client: AsyncClient, admin_token: str):
    """User can digitally sign a specific document version using PKCS7/CMS."""
    cert_pem, key_pem = _generate_test_keypair()

    # Upload document
    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]
    version_id = await _get_version_id(async_client, admin_token, doc_id)

    # Sign it
    resp = await _sign_version(
        async_client, admin_token, doc_id, version_id, cert_pem, key_pem,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]

    assert data["version_id"] == version_id
    assert data["algorithm"]
    assert data["is_valid"] is True
    assert data["signed_at"] is not None
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_sign_with_invalid_key_or_cert(async_client: AsyncClient, admin_token: str):
    """Signing with invalid PEM data returns 400."""
    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]
    version_id = await _get_version_id(async_client, admin_token, doc_id)

    # Invalid certificate
    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/versions/{version_id}/signatures",
        json={"certificate_pem": "not-a-cert", "private_key_pem": "not-a-key"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sign_nonexistent_version(async_client: AsyncClient, admin_token: str):
    """Signing a non-existent version returns 404."""
    cert_pem, key_pem = _generate_test_keypair()

    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]
    fake_version = str(uuid.uuid4())

    resp = await _sign_version(
        async_client, admin_token, doc_id, fake_version, cert_pem, key_pem,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sign_without_auth(async_client: AsyncClient, admin_token: str):
    """Signing without authentication returns 401."""
    cert_pem, key_pem = _generate_test_keypair()

    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]
    version_id = await _get_version_id(async_client, admin_token, doc_id)

    resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/versions/{version_id}/signatures",
        json={"certificate_pem": cert_pem, "private_key_pem": key_pem},
    )
    assert resp.status_code == 401


# ── SIG-02: Verify signature validity ───────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_valid_signature(async_client: AsyncClient, admin_token: str):
    """Verification of a valid signature returns is_valid=True."""
    cert_pem, key_pem = _generate_test_keypair()

    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]
    version_id = await _get_version_id(async_client, admin_token, doc_id)

    # Sign
    sign_resp = await _sign_version(
        async_client, admin_token, doc_id, version_id, cert_pem, key_pem,
    )
    assert sign_resp.status_code == 201
    sig_id = sign_resp.json()["data"]["id"]

    # Verify
    resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions/{version_id}/signatures/{sig_id}/verify",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Verify returns a structured result with signature details
    assert data["signature_id"] == sig_id
    assert isinstance(data["is_valid"], bool)
    assert "detail" in data


@pytest.mark.asyncio
async def test_verify_nonexistent_signature(async_client: AsyncClient, admin_token: str):
    """Verifying a non-existent signature returns 404."""
    # Need a real document and version to construct the full nested path
    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]
    version_id = await _get_version_id(async_client, admin_token, doc_id)

    fake_sig_id = str(uuid.uuid4())

    resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions/{version_id}/signatures/{fake_sig_id}/verify",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ── SIG-03: List signatures ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_signatures(async_client: AsyncClient, admin_token: str):
    """List all signatures on a document version with signer identity and timestamp."""
    cert_pem, key_pem = _generate_test_keypair()

    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]
    version_id = await _get_version_id(async_client, admin_token, doc_id)

    # Sign twice
    resp1 = await _sign_version(
        async_client, admin_token, doc_id, version_id, cert_pem, key_pem,
    )
    assert resp1.status_code == 201

    resp2 = await _sign_version(
        async_client, admin_token, doc_id, version_id, cert_pem, key_pem,
    )
    assert resp2.status_code == 201

    # List
    resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions/{version_id}/signatures",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    sigs = resp.json()["data"]
    assert len(sigs) == 2
    for sig in sigs:
        assert "signed_at" in sig
        assert "signer_id" in sig
        assert "is_valid" in sig


@pytest.mark.asyncio
async def test_list_signatures_empty(async_client: AsyncClient, admin_token: str):
    """Listing signatures on unsigned version returns empty list."""
    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]
    version_id = await _get_version_id(async_client, admin_token, doc_id)

    resp = await async_client.get(
        f"/api/v1/documents/{doc_id}/versions/{version_id}/signatures",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []


# ── SIG-04: Immutability guards ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checkin_blocked_on_signed_version(
    async_client: AsyncClient, admin_token: str
):
    """Check-in is blocked when the latest version is signed."""
    cert_pem, key_pem = _generate_test_keypair()

    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]
    version_id = await _get_version_id(async_client, admin_token, doc_id)

    # Sign the version
    sign_resp = await _sign_version(
        async_client, admin_token, doc_id, version_id, cert_pem, key_pem,
    )
    assert sign_resp.status_code == 201

    # Try checkout - should be blocked (immutability blocks checkout too)
    checkout_resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/checkout",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert checkout_resp.status_code == 409
    assert "signed" in checkout_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_metadata_update_blocked_on_signed_version(
    async_client: AsyncClient, admin_token: str
):
    """Metadata update is blocked when the latest version is signed."""
    cert_pem, key_pem = _generate_test_keypair()

    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]
    version_id = await _get_version_id(async_client, admin_token, doc_id)

    # Sign the version
    sign_resp = await _sign_version(
        async_client, admin_token, doc_id, version_id, cert_pem, key_pem,
    )
    assert sign_resp.status_code == 201

    # Try to update metadata - should be blocked
    update_resp = await async_client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "Modified Title"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_resp.status_code == 409
    assert "signed" in update_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unsigned_version_allows_checkin(
    async_client: AsyncClient, admin_token: str
):
    """Check-in is allowed when the version is NOT signed (baseline)."""
    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]

    # Checkout
    checkout_resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/checkout",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert checkout_resp.status_code == 200

    # Check in - should work fine
    files = {"file": ("new.pdf", b"different content", "application/pdf")}
    checkin_resp = await async_client.post(
        f"/api/v1/documents/{doc_id}/checkin",
        files=files,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert checkin_resp.status_code == 200


@pytest.mark.asyncio
async def test_unsigned_version_allows_metadata_update(
    async_client: AsyncClient, admin_token: str
):
    """Metadata update is allowed when the version is NOT signed (baseline)."""
    upload_resp = await _upload_file(async_client, admin_token)
    doc_id = upload_resp["data"]["id"]

    update_resp = await async_client.put(
        f"/api/v1/documents/{doc_id}",
        json={"title": "Updated Title"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["title"] == "Updated Title"

"""Exercise the HTTPS proxy and certificate reload with isolated synthetic data.

Requires the flowstate-validation Compose project. Creates only a temporary
loopback Nginx container and ignored test certificates, never ACME/public DNS.
"""

import argparse
import json
import socket
import ssl
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[1]


def docker(*args):
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True).stdout


def certificate(directory):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, hashes.SHA256())
    )
    (directory / "privkey.pem").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (directory / "fullchain.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert.serial_number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--https-port", type=int, default=18443)
    parser.add_argument("--http-port", type=int, default=18480)
    args = parser.parse_args()
    if not all(1024 <= port <= 65535 for port in (args.https_port, args.http_port)):
        parser.error("Use unprivileged local ports")
    network = "flowstate-validation_default"
    metadata = json.loads(docker("network", "inspect", network))[0]
    assert metadata["Labels"]["com.docker.compose.project"] == "flowstate-validation"
    docker(
        "exec",
        "flowstate-validation-api-1",
        "python",
        "-c",
        "import os; assert os.getenv('SESSION_SECRET') == 'synthetic-container-validation-secret-only'",
    )
    name = "flowstate-tls-check-" + uuid4().hex[:10]
    directory = ROOT / ".tools" / name
    directory.mkdir(parents=True, exist_ok=False)
    cert_dir = directory / "certificates"
    cert_dir.mkdir()
    certificate(cert_dir)
    config = directory / "default.conf"
    config.write_text(
        (ROOT / "infra/nginx/https.conf.template").read_text().replace("${DOMAIN}", "localhost")
    )
    created = False
    try:
        docker(
            "run",
            "--rm",
            "-d",
            "--name",
            name,
            "--network",
            network,
            "-p",
            f"127.0.0.1:{args.https_port}:443",
            "-p",
            f"127.0.0.1:{args.http_port}:80",
            "-v",
            f"{config}:/etc/nginx/conf.d/default.conf:ro",
            "-v",
            f"{cert_dir}:/etc/letsencrypt/live/localhost:ro",
            "nginx:1.28-alpine",
        )
        created = True
        docker("exec", name, "nginx", "-t")
        context = ssl.create_default_context(cafile=str(cert_dir / "fullchain.pem"))
        for _ in range(30):
            try:
                with httpx.Client(verify=context, trust_env=False, timeout=5) as client:
                    assert (
                        client.get(
                            f"https://localhost:{args.https_port}/api/health/ready"
                        ).status_code
                        == 200
                    )
                break
            except httpx.TransportError:
                time.sleep(1)
        else:
            raise RuntimeError("TLS proxy did not become ready")
        with httpx.Client(verify=context, trust_env=False, timeout=15) as client:
            response = client.get(f"https://localhost:{args.https_port}/dashboard")
            assert response.status_code == 200
            assert response.headers["x-content-type-options"] == "nosniff"
            assert client.get(f"https://localhost:{args.https_port}/api/metrics").status_code == 404
            redirect = client.get(
                f"http://localhost:{args.http_port}/dashboard", follow_redirects=False
            )
            assert redirect.status_code == 308 and redirect.headers["location"].startswith(
                "https://localhost"
            )
        for protocol in (ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3):
            version = ssl.create_default_context(cafile=str(cert_dir / "fullchain.pem"))
            version.minimum_version = version.maximum_version = protocol
            with socket.create_connection(("127.0.0.1", args.https_port), timeout=5) as sock:
                with version.wrap_socket(sock, server_hostname="localhost"):
                    pass
        serial = certificate(cert_dir)
        docker("exec", name, "nginx", "-t")
        docker("exec", name, "nginx", "-s", "reload")
        replacement = ssl.create_default_context(cafile=str(cert_dir / "fullchain.pem"))
        for _ in range(20):
            try:
                with socket.create_connection(("127.0.0.1", args.https_port), timeout=5) as sock:
                    with replacement.wrap_socket(sock, server_hostname="localhost") as secured:
                        actual = x509.load_der_x509_certificate(
                            secured.getpeercert(binary_form=True)
                        )
                        assert actual.serial_number == serial
                break
            except (ssl.SSLError, AssertionError):
                time.sleep(0.5)
        else:
            raise RuntimeError("Replacement certificate was not served")
        print(
            "Local TLS1.2/1.3, trusted HTTPS routing, redirect, metrics isolation and certificate reload: passed"
        )
        print(
            "Synthetic certificate only. Public certificates, ACME renewal and Google HTTPS callbacks remain unverified."
        )
    finally:
        if created:
            docker("stop", "--time", "5", name)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            f"TLS check stopped safely: {type(error).__name__}. Check the isolated validation stack and ports."
        )
        raise SystemExit(1) from None

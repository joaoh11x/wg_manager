"""Sincroniza interfaces e peers WireGuard do MikroTik para o banco (SQLAlchemy).

Use quando você importar/criar uma interface/peers diretamente no MikroTik e o
frontend enxergar via API, mas o banco ainda não tiver os registros.

Execução:
  python3 sync_mikrotik_import.py

Requer no .env (ou env vars):
  MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS

Opcional:
    DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker

# Allow running this script directly: ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models.interface import Interface
from app.models.peer import Peer
from app.utils.database import DatabaseConnection
from app.utils.mikrotik_api import MikroTikAPI


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_listen_port(mk_interface: dict[str, Any]) -> int:
    # RouterOS costuma retornar "listen-port"
    return _to_int(mk_interface.get("listen-port") or mk_interface.get("listen_port"), 13231)


def _extract_ip_from_allowed_address(allowed: str | None) -> Optional[str]:
    if not allowed:
        return None

    # Pode vir como "10.0.0.2/32" ou "10.0.0.2/32,10.0.0.3/32"
    first = allowed.split(",")[0].strip()
    if not first:
        return None

    ip = first.split("/")[0].strip()
    return ip or None


_slug_re = re.compile(r"[^a-z0-9._-]+")


def _default_email(peer_name: str | None, public_key: str) -> str:
    # Email determinístico e único por public_key
    digest = hashlib.sha256(public_key.encode("utf-8")).hexdigest()[:16]
    base = (peer_name or "peer").strip().lower()
    base = _slug_re.sub("-", base).strip("-")
    base = base[:24] or "peer"
    return f"{base}-{digest}@imported.local"


def _ensure_unique_email(session, desired_email: str, peer_id: int | None = None) -> str:
    email = desired_email
    suffix = 1

    while True:
        q = session.query(Peer).filter(Peer.email == email)
        if peer_id is not None:
            q = q.filter(Peer.id != peer_id)
        if q.first() is None:
            return email

        local, _, domain = desired_email.partition("@")
        email = f"{local}-{suffix}@{domain}"
        suffix += 1


def sync(database_url: str, dry_run: bool = False) -> dict[str, int]:
    mk = MikroTikAPI()
    db = DatabaseConnection(database_url)
    # Avoid query-triggered autoflush while we're still building upserts.
    Session = sessionmaker(bind=db.engine, autoflush=False)

    created_interfaces = 0
    updated_interfaces = 0
    created_peers = 0
    updated_peers = 0
    skipped_peers = 0
    conflicted_peers = 0
    conflict_examples: list[str] = []

    # Track IPs we've already assigned during this run (MikroTik can contain duplicates).
    ip_owner: dict[str, str] = {}

    session = Session()
    try:
        # 1) Interfaces
        mk_interfaces = mk.list_interfaces() or []
        for mk_intf in mk_interfaces:
            name = (mk_intf or {}).get("name")
            if not name:
                continue

            listen_port = _extract_listen_port(mk_intf)
            iface = session.query(Interface).filter_by(name=name).first()
            if not iface:
                iface = Interface(name=name, listen_port=listen_port)
                session.add(iface)
                created_interfaces += 1
            else:
                if iface.listen_port != listen_port:
                    iface.listen_port = listen_port
                    updated_interfaces += 1

        session.flush()  # garante ids

        # 2) Peers
        mk_peers = mk.list_wireguard_peers() or []
        for mk_peer in mk_peers:
            peer_name = (mk_peer or {}).get("name")
            interface_name = (mk_peer or {}).get("interface")
            public_key = (mk_peer or {}).get("public-key")
            allowed = (mk_peer or {}).get("allowed-address")
            ip_address = _extract_ip_from_allowed_address(allowed)

            if not public_key or not ip_address:
                skipped_peers += 1
                continue

            # MikroTik may contain duplicate allowed-address IPs; SQLite enforces UNIQUE(ip_address).
            existing_owner = ip_owner.get(ip_address)
            if existing_owner and existing_owner != public_key:
                conflicted_peers += 1
                if len(conflict_examples) < 20:
                    conflict_examples.append(
                        f"IP duplicado {ip_address} em peers diferentes (public-key {existing_owner[:10]}... vs {public_key[:10]}...)"
                    )
                continue
            ip_owner[ip_address] = public_key

            # garantir interface no DB
            interface_id = None
            if interface_name:
                iface = session.query(Interface).filter_by(name=interface_name).first()
                if not iface:
                    # se não veio no list_interfaces (edge-case), cria com porta default
                    iface = Interface(name=interface_name, listen_port=13231)
                    session.add(iface)
                    session.flush()
                    created_interfaces += 1
                interface_id = iface.id

            # Prefer match by public_key (strongest), then ip_address (unique), then name (weak)
            peer = session.query(Peer).filter_by(public_key=public_key).first()
            if not peer:
                peer = session.query(Peer).filter_by(ip_address=ip_address).first()
            if not peer and peer_name:
                peer = session.query(Peer).filter_by(name=peer_name).first()

            desired_email = _default_email(peer_name, public_key)

            if not peer:
                email = _ensure_unique_email(session, desired_email)
                peer = Peer(
                    name=peer_name or public_key[:16],
                    email=email,
                    public_key=public_key,
                    ip_address=ip_address,
                    interface_id=interface_id,
                    group_id=None,
                    user_id=None,
                )
                session.add(peer)
                created_peers += 1
            else:
                changed = False

                # If we matched by ip_address but public_key differs, do not overwrite silently.
                # This indicates inconsistent data in DB vs MikroTik.
                if peer.public_key and peer.public_key != public_key:
                    conflicted_peers += 1
                    continue

                if not peer.public_key:
                    peer.public_key = public_key
                    changed = True

                # Ajusta campos básicos sem sobrescrever email manual existente
                if peer.name != (peer_name or peer.name):
                    peer.name = peer_name or peer.name
                    changed = True

                if peer.ip_address != ip_address:
                    # Only update if target IP isn't already used by another record.
                    other = session.query(Peer).filter(Peer.ip_address == ip_address, Peer.id != peer.id).first()
                    if other is None:
                        peer.ip_address = ip_address
                        changed = True
                    else:
                        conflicted_peers += 1
                        if len(conflict_examples) < 20:
                            conflict_examples.append(
                                f"Conflito no DB: IP {ip_address} já usado por Peer.id={other.id}"
                            )

                if interface_id is not None and peer.interface_id != interface_id:
                    peer.interface_id = interface_id
                    changed = True

                # Se email estiver vazio (não deveria), preenche
                if not peer.email:
                    peer.email = _ensure_unique_email(session, desired_email, peer_id=peer.id)
                    changed = True

                if changed:
                    updated_peers += 1

        if dry_run:
            session.rollback()
        else:
            session.commit()

        result = {
            "created_interfaces": created_interfaces,
            "updated_interfaces": updated_interfaces,
            "created_peers": created_peers,
            "updated_peers": updated_peers,
            "skipped_peers": skipped_peers,
            "conflicted_peers": conflicted_peers,
        }

        # Print small hint list for conflicts (kept small to avoid noisy output)
        if conflict_examples:
            print("Conflitos detectados (exemplos):")
            for item in conflict_examples:
                print(f"- {item}")

        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Sync MikroTik WireGuard interfaces/peers into database")
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URI"),
        help="URL do banco. Ex.: postgresql+psycopg://user:pass@host:5432/dbname",
    )
    parser.add_argument("--dry-run", action="store_true", help="Não grava no banco (rollback no final)")
    args = parser.parse_args()

    if not args.db_url:
        raise SystemExit(
            "DATABASE_URL/--db-url não informado. Ex.: postgresql+psycopg://user:pass@localhost:5432/wireguard_manager"
        )

    result = sync(database_url=args.db_url, dry_run=args.dry_run)

    mode = "DRY-RUN" if args.dry_run else "OK"
    print(f"[{mode}] Sync finalizado")
    print(
        "Interfaces: +{created_interfaces} / ~{updated_interfaces} | "
        "Peers: +{created_peers} / ~{updated_peers} | pulados: {skipped_peers} | conflitos: {conflicted_peers}".format(**result)
    )


if __name__ == "__main__":
    main()

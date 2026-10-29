"""Integração com a OCI: segredos do OCI Vault e documentos do Object Storage.

Na VM da OCI, a autenticação usa instance principal: a própria instância se
identifica, sem chave de API gravada em disco. Para testar fora da OCI, defina
NEXUS_OCI_AUTH=config e use o ~/.oci/config.

O SDK `oci` é opcional (extra `oci` do pyproject) e só é importado aqui.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger("nexus_ai")


@lru_cache(maxsize=1)
def _auth() -> dict[str, Any]:
    try:
        import oci
    except ImportError as exc:
        raise RuntimeError("Instale o extra 'oci' (uv sync --extra oci).") from exc

    if os.getenv("NEXUS_OCI_AUTH", "").strip().lower() == "config":
        return {"config": oci.config.from_file()}
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    return {"config": {"region": signer.region}, "signer": signer}


def ler_segredo(secret_ocid: str, client: Any | None = None) -> str:
    """Lê o conteúdo (texto) da versão atual de um segredo do OCI Vault."""
    if client is None:
        import oci

        client = oci.secrets.SecretsClient(**_auth())
    bundle = client.get_secret_bundle(secret_ocid).data
    content = bundle.secret_bundle_content.content
    return base64.b64decode(content).decode("utf-8").strip()


def _md5_base64(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return base64.b64encode(digest.digest()).decode("ascii")


def _listar_objetos(client: Any, namespace: str, bucket: str, prefixo: str) -> list[Any]:
    objetos: list[Any] = []
    start = None
    while True:
        page = client.list_objects(
            namespace,
            bucket,
            prefix=prefixo or None,
            start=start,
            fields="name,md5,timeModified",
        ).data
        objetos.extend(page.objects)
        start = page.next_start_with
        if not start:
            return objetos


def baixar_documentos(
    bucket: str,
    destino: str | Path,
    prefixo: str = "",
    client: Any | None = None,
) -> dict[str, list[str]]:
    """Espelha os objetos do bucket na pasta local de documentos.

    Baixa só objetos novos ou com MD5 diferente e apaga os arquivos locais que
    não existem mais no bucket. A indexação fica com `sync_directory`, que
    compara o conteúdo e reindexa apenas o que mudou.
    """
    if client is None:
        import oci

        client = oci.object_storage.ObjectStorageClient(**_auth())

    root = Path(destino).resolve()
    namespace = client.get_namespace().data
    objetos = _listar_objetos(client, namespace, bucket, prefixo)
    resumo: dict[str, list[str]] = {"baixados": [], "removidos": []}

    # Bucket vazio quase sempre é configuração errada; apagar tudo esvaziaria o índice.
    if not objetos:
        logger.warning("Bucket %s sem objetos em '%s'; pasta local mantida.", bucket, prefixo)
        return resumo

    remotos: set[Path] = set()
    for objeto in objetos:
        relativo = objeto.name[len(prefixo):].lstrip("/")
        if not relativo or relativo.endswith("/"):
            continue
        caminho = (root / relativo).resolve()
        if not caminho.is_relative_to(root):
            logger.warning("Objeto ignorado, fora da pasta de documentos: %s", objeto.name)
            continue
        remotos.add(caminho)
        if caminho.is_file() and objeto.md5 and _md5_base64(caminho) == objeto.md5:
            continue

        caminho.parent.mkdir(parents=True, exist_ok=True)
        parcial = caminho.with_name(caminho.name + ".part")
        resposta = client.get_object(namespace, bucket, objeto.name)
        with parcial.open("wb") as file:
            for bloco in resposta.data.raw.stream(1024 * 1024, decode_content=False):
                file.write(bloco)
        parcial.replace(caminho)
        # A data do bucket vira a data do arquivo: é ela que aparece em "atualizado
        # em" nas fontes e que a curadoria compara com a última revisão.
        if objeto.time_modified:
            momento = objeto.time_modified.timestamp()
            os.utime(caminho, (momento, momento))
        resumo["baixados"].append(relativo)

    for local in sorted(root.rglob("*")):
        if local.is_file() and local.resolve() not in remotos:
            local.unlink()
            resumo["removidos"].append(local.relative_to(root).as_posix())
    return resumo

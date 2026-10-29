import base64
import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import nexus_ai.config as config
from nexus_ai.oci_cloud import baixar_documentos, ler_segredo

MODIFICADO = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def _md5(conteudo: bytes) -> str:
    return base64.b64encode(hashlib.md5(conteudo).digest()).decode("ascii")


class FakeSecretsClient:
    def get_secret_bundle(self, secret_ocid):
        content = base64.b64encode(f"gsk_{secret_ocid}\n".encode()).decode()
        return SimpleNamespace(
            data=SimpleNamespace(secret_bundle_content=SimpleNamespace(content=content))
        )


class FakeObjectStorage:
    """Bucket em memória com a mesma interface usada do ObjectStorageClient."""

    def __init__(self, objetos: dict[str, bytes], page_size: int = 2):
        self.objetos = objetos
        self.page_size = page_size
        self.downloads: list[str] = []

    def get_namespace(self):
        return SimpleNamespace(data="ns")

    def list_objects(self, namespace, bucket, prefix=None, start=None, fields=None):
        nomes = sorted(n for n in self.objetos if not prefix or n.startswith(prefix))
        inicio = nomes.index(start) if start else 0
        pagina = nomes[inicio:inicio + self.page_size]
        proximo = nomes[inicio + self.page_size] if inicio + self.page_size < len(nomes) else None
        return SimpleNamespace(
            data=SimpleNamespace(
                objects=[
                    SimpleNamespace(name=n, md5=_md5(self.objetos[n]), time_modified=MODIFICADO)
                    for n in pagina
                ],
                next_start_with=proximo,
            )
        )

    def get_object(self, namespace, bucket, name):
        self.downloads.append(name)
        conteudo = self.objetos[name]
        raw = SimpleNamespace(stream=lambda size, decode_content=False: iter([conteudo]))
        return SimpleNamespace(data=SimpleNamespace(raw=raw))


def test_ler_segredo_decodifica_base64():
    assert ler_segredo("abc", client=FakeSecretsClient()) == "gsk_abc"


def test_baixar_documentos_espelha_bucket(tmp_path):
    client = FakeObjectStorage(
        {
            "docs/suporte/faq.md": b"faq",
            "docs/comercial/precos.csv": b"plano,preco",
            "docs/contatos.md": b"contatos",
        }
    )
    (tmp_path / "antigo.md").write_text("removido do bucket")

    resumo = baixar_documentos("bucket", tmp_path, "docs/", client=client)

    assert sorted(resumo["baixados"]) == ["comercial/precos.csv", "contatos.md", "suporte/faq.md"]
    assert resumo["removidos"] == ["antigo.md"]
    assert (tmp_path / "suporte" / "faq.md").read_bytes() == b"faq"
    assert (tmp_path / "contatos.md").stat().st_mtime == MODIFICADO.timestamp()


def test_baixar_documentos_ignora_arquivos_iguais(tmp_path):
    client = FakeObjectStorage({"faq.md": b"faq", "precos.csv": b"v1"})
    baixar_documentos("bucket", tmp_path, client=client)
    client.objetos["precos.csv"] = b"v2"
    client.downloads.clear()

    resumo = baixar_documentos("bucket", tmp_path, client=client)

    assert resumo["baixados"] == ["precos.csv"]
    assert client.downloads == ["precos.csv"]


def test_bucket_vazio_nao_apaga_pasta_local(tmp_path):
    (tmp_path / "faq.md").write_text("faq")

    resumo = baixar_documentos("bucket", tmp_path, client=FakeObjectStorage({}))

    assert resumo == {"baixados": [], "removidos": []}
    assert (tmp_path / "faq.md").exists()


def test_objeto_fora_da_pasta_e_ignorado(tmp_path):
    destino = tmp_path / "documentos"
    destino.mkdir()
    client = FakeObjectStorage({"../fora.md": b"x", "ok.md": b"ok"})

    resumo = baixar_documentos("bucket", destino, client=client)

    assert resumo["baixados"] == ["ok.md"]
    assert not (tmp_path / "fora.md").exists()


def test_groq_api_key_vem_do_vault(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("NEXUS_GROQ_SECRET_OCID", "ocid1.vaultsecret.teste")
    monkeypatch.setattr(
        "nexus_ai.oci_cloud.ler_segredo", lambda ocid: f"gsk_{ocid}"
    )
    config._segredo_do_vault.cache_clear()

    assert config.get_groq_api_key() == "gsk_ocid1.vaultsecret.teste"
    config._segredo_do_vault.cache_clear()


def test_groq_api_key_do_env_tem_prioridade(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_local")
    monkeypatch.setenv("NEXUS_GROQ_SECRET_OCID", "ocid1.vaultsecret.teste")
    assert config.get_groq_api_key() == "gsk_local"


def test_documents_bucket(monkeypatch):
    monkeypatch.delenv("NEXUS_DOCUMENTS_BUCKET", raising=False)
    assert config.get_documents_bucket() is None
    monkeypatch.setenv("NEXUS_DOCUMENTS_BUCKET", " nexus-documentos ")
    monkeypatch.setenv("NEXUS_DOCUMENTS_PREFIX", "documents/")
    assert config.get_documents_bucket() == ("nexus-documentos", "documents/")


@pytest.fixture(autouse=True)
def sem_segredo_do_ambiente(monkeypatch):
    monkeypatch.delenv("NEXUS_GROQ_SECRET_OCID", raising=False)

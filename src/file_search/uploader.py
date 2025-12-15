import logging
import os
import tempfile
from typing import List, Dict, Any, Optional

from src.config.app_config import FileSearchConfig, get_config


class FileSearchUploader:
    """
    Gemini File Search へのアップロードを担当するクラス。
    - store(=data store) を display_name で作成/再利用
    - ファイルをアップロードし、store に取り込む
    - 100MB 制限に合わせて本文はそのままテキストとして送る
    """

    def __init__(self, config: Optional[FileSearchConfig] = None):
        self.config = config or get_config().file_search
        self.logger = logging.getLogger("file_search_uploader")
        self._client = None
        self._store_name: Optional[str] = None

    @property
    def enabled(self) -> bool:
        return self.config.enabled and bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))

    def _client_or_raise(self):
        if self._client is None:
            from google import genai

            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GOOGLE_API_KEY もしくは GEMINI_API_KEY が設定されていません")

            self._client = genai.Client(
                api_key=api_key,
                http_options={"api_version": "v1alpha"},  # File Searchはv1alpha
            )
        return self._client

    def _ensure_store(self):
        """
        display_name でストアを探し、無ければ作成。
        APIキーのみで動く v1alpha のシンプルAPIを使用する。
        """
        if self._store_name:
            return self._store_name

        client = self._client_or_raise()
        display = self.config.store_name or "market-news-store"

        stores = client.file_search_stores.list()
        for st in stores:
            if getattr(st, "display_name", "") == display:
                self._store_name = st.name
                self.logger.info(f"既存 File Search Store を利用: {st.name}")
                return self._store_name

        store = client.file_search_stores.create(
            config={"display_name": display}
        )
        self._store_name = store.name
        self.logger.info(f"File Search Store を新規作成: {store.name}")
        return self._store_name

    def upload_articles(self, articles: List[Dict[str, Any]], doc_date: Optional[str] = None) -> Dict[str, Any]:
        """
        記事を File Search にアップロードする。
        - 1記事 = 1ファイル としてアップロード
        - メタデータを custom_metadata に付与
        """
        if not self.enabled:
            return {"uploaded": 0, "skipped": len(articles), "reason": "file_search_disabled"}

        if not articles:
            return {"uploaded": 0, "skipped": 0}

        store_name = self._ensure_store()
        client = self._client_or_raise()

        uploaded = 0
        skipped = 0
        errors = []

        for article in articles:
            title = article.get("title") or "untitled"
            content = article.get("content") or article.get("body") or ""
            if not content.strip():
                skipped += 1
                continue

            text = self._format_article_text(article)

            try:
                with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as tf:
                    tf.write(text)
                    tmp_path = tf.name

                # custom_metadata は key/value のリスト形式
                metadata = []
                for k, v in {
                    "source": article.get("source", ""),
                    "url": article.get("url", ""),
                    "published_at": str(article.get("published_at") or article.get("published_jst") or ""),
                    "doc_date": doc_date or "",
                    "category": article.get("category", ""),
                    "region": article.get("region", ""),
                }.items():
                    metadata.append({"key": k, "string_value": v})

                op = client.file_search_stores.upload_to_file_search_store(
                    file_search_store_name=store_name,
                    file=tmp_path,
                    config={
                        "display_name": title[:128],
                        "mime_type": "text/plain",
                        "custom_metadata": metadata,
                    },
                )
                # Operationは即時doneになることが多い。doneフラグを確認するだけにする。
                if not getattr(op, "done", True):
                    self.logger.info("File Search upload operation in progress; skipping wait")
                uploaded += 1

            except Exception as e:
                errors.append(str(e))
                self.logger.error(f"File Search upload failed: {e}")
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        return {"uploaded": uploaded, "skipped": skipped, "errors": errors}

    def _format_article_text(self, article: Dict[str, Any]) -> str:
        parts = []
        parts.append(article.get("title", ""))
        parts.append(article.get("summary", ""))  # あれば
        body = article.get("content") or article.get("body") or ""
        parts.append(body)
        return "\n\n".join([p for p in parts if p])

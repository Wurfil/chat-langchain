"""Load html from files, clean up, split, ingest into Chroma."""
import logging
import os
import re
from pathlib import Path

from parser import langchain_docs_extractor

from bs4 import BeautifulSoup, SoupStrainer
from langchain_community.document_loaders import SitemapLoader, RecursiveUrlLoader
from langchain.indexes import SQLRecordManager, index
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.utils.html import PREFIXES_TO_IGNORE_REGEX, SUFFIXES_TO_IGNORE_REGEX
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SitemapLoaderWithChromium(SitemapLoader):
    async def _fetch(
        self, url: str, retries: int = 3, cooldown: int = 2, backoff: float = 1.5
    ) -> str:
        """
        Asynchronously scrape the content of a given URL using Playwright's async API.

        Args:
            url (str): The URL to scrape.

        Returns:
            str: The scraped HTML content or an error message if an exception occurs.

        """
        from playwright.async_api import async_playwright

        logger.info("Starting scraping...")
        results = ""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url)
                results = await page.content()  # Simply get the HTML content
                logger.info("Content scraped")
            except Exception as e:
                results = f"Error: {e}"
            await browser.close()
        return results


def get_embeddings_model() -> Embeddings:
    return HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small")


def metadata_extractor(meta: dict, soup: BeautifulSoup) -> dict:
    title = soup.find("title")
    description = soup.find("meta", attrs={"name": "description"})
    html = soup.find("html")
    return {
        "source": meta["loc"],
        "title": title.get_text() if title else "",
        "description": description.get("content", "") if description else "",
        "language": html.get("lang", "") if html else "",
        **meta,
    }


def load_rustore_docs():
    file_path = Path("./notebooks/sitemap-help.xml").absolute()
    return SitemapLoaderWithChromium(
        file_path,
        is_local=True,
        filter_urls=["https://www.rustore.ru/help"],
        parsing_function=langchain_docs_extractor,
        default_parser="lxml",
        bs_kwargs={
            "parse_only": SoupStrainer(
                name=("article", "title", "html", "lang", "content")
            ),
        },
        meta_function=metadata_extractor,
        requests_per_second=1,
    ).load()


def load_rustore_example_doc():
    with open('notebooks/test.html', "r") as f:
        soup = BeautifulSoup(f)
    metadata = metadata_extractor(
        {"loc": "https://www.rustore.ru/help/sdk/push-notifications/user-segments/segments-mytracker"
         }, soup)
    content = langchain_docs_extractor(soup)

    doc = Document(page_content=content, metadata=metadata)
    return [doc]


def load_langsmith_docs():
    return RecursiveUrlLoader(
        url="https://www.rustore.ru/help/developers/",
        max_depth=8,
        extractor=simple_extractor,
        prevent_outside=True,
        use_async=True,
        timeout=600,
        # Drop trailing / to avoid duplicate pages.
        link_regex=(
            f"href=[\"']{PREFIXES_TO_IGNORE_REGEX}((?:{SUFFIXES_TO_IGNORE_REGEX}.)*?)"
            r"(?:[\#'\"]|\/[\#'\"])"
        ),
        check_response_status=True,
    ).load()


def simple_extractor(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return re.sub(r"\n\n+", "\n\n", soup.text).strip()


def load_api_docs():
    return RecursiveUrlLoader(
        url="https://api.python.langchain.com/en/latest/",
        max_depth=8,
        extractor=simple_extractor,
        prevent_outside=True,
        use_async=True,
        timeout=600,
        # Drop trailing / to avoid duplicate pages.
        link_regex=(
            f"href=[\"']{PREFIXES_TO_IGNORE_REGEX}((?:{SUFFIXES_TO_IGNORE_REGEX}.)*?)"
            r"(?:[\#'\"]|\/[\#'\"])"
        ),
        check_response_status=True,
        exclude_dirs=(
            "https://api.python.langchain.com/en/latest/_sources",
            "https://api.python.langchain.com/en/latest/_modules",
        ),
    ).load()


def ingest_docs():
    DATABASE_HOST = "0.0.0.0"
    DATABASE_PORT = "5432"
    DATABASE_USERNAME = "postgres"
    DATABASE_PASSWORD = "hackme"
    DATABASE_NAME = "rustore"
    RECORD_MANAGER_DB_URL = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
    COLLECTION_NAME = "test_collection"

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)
    embedding = get_embeddings_model()

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embedding,
        persist_directory='./chroma_data'
    )

    record_manager = SQLRecordManager(
        f"chroma/{COLLECTION_NAME}", db_url=RECORD_MANAGER_DB_URL
    )
    record_manager.create_schema()

    docs_from_documentation = load_rustore_docs()
    logger.info(f"Loaded {len(docs_from_documentation)} docs from documentation")
    # docs_from_api = load_api_docs()
    # logger.info(f"Loaded {len(docs_from_api)} docs from API")
    # docs_from_langsmith = load_langsmith_docs()
    # logger.info(f"Loaded {len(docs_from_langsmith)} docs from Langsmith")

    # docs_transformed = text_splitter.split_documents(
    #     docs_from_documentation + docs_from_api + docs_from_langsmith
    # )

    docs_transformed = text_splitter.split_documents(
        docs_from_documentation
    )
    docs_transformed = [doc for doc in docs_transformed if len(doc.page_content) > 10]

    for doc in docs_transformed:
        if "source" not in doc.metadata:
            doc.metadata["source"] = ""
        if "title" not in doc.metadata:
            doc.metadata["title"] = ""

    indexing_stats = index(
        docs_transformed,
        record_manager,
        vectorstore,
        cleanup="full",
        source_id_key="source",
        force_update=(os.environ.get("FORCE_UPDATE") or "false").lower() == "true",
    )

    logger.info(f"Indexing stats: {indexing_stats}")
    num_vecs = len(vectorstore)
    logger.info(
        f"LangChain now has this many vectors: {num_vecs}",
    )


if __name__ == "__main__":
    ingest_docs()

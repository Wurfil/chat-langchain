import re
from typing import Generator

from bs4 import BeautifulSoup, Doctype, NavigableString, Tag


def langchain_docs_extractor(soup: BeautifulSoup) -> str:
    # Remove all the tags that are not meaningful for the extraction.
    SCAPE_TAGS = ["nav", "footer", "aside", "script", "style"]
    [tag.decompose() for tag in soup.find_all(SCAPE_TAGS)]

    def get_text(tag: Tag) -> Generator[str, None, None]:
        for child in tag.children:
            if isinstance(child, NavigableString):
                yield child
            elif isinstance(child, Tag):
                if child.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    yield f"{'#' * int(child.name[1:])} {child.get_text().strip()}\n\n"
                elif child.name == "a":
                    yield f"[{child.get_text(strip=False)}]({child.get('href')})"
                elif child.name == "img":
                    yield f"![{child.get('alt', '')}]({child.get('src')})"
                elif child.name in ["strong", "b"]:
                    yield f"**{child.get_text(strip=False)}**"
                elif child.name in ["em", "i"]:
                    yield f"_{child.get_text(strip=False)}_"
                elif child.name == "br":
                    yield "\n"
                elif child.name == "code":
                    if child.parent.name == "pre":
                        # Обработка блоков кода
                        language = child.parent.get('class', [''])[0].split('-')[-1]
                        code_content = child.get_text(strip=True)
                        yield f"```{language}\n{code_content}\n```\n\n"
                    else:
                        yield f"`{child.get_text(strip=False)}`"
                elif child.name == "p":
                    yield from get_text(child)
                    yield "\n\n"
                elif child.name in ["ul", "ol"]:
                    for li in child.find_all("li", recursive=False):
                        prefix = "- " if child.name == "ul" else f"{li.parent.index(li) + 1}. "
                        yield prefix
                        yield from get_text(li)
                        yield "\n"
                    yield "\n"
                elif child.name == "div" and "prism-code" in child.get("class", []):
                    # Обработка блоков кода Prism
                    language = child.get('class', [])
                    language = next((c for c in language if c.startswith("language-")), "")
                    language = language.split("-")[-1] if language else ""
                    code_content = child.get_text(strip=True)
                    yield f"```{language}\n{code_content}\n```\n\n"
                elif child.name == "img" and "img__desktop" in child.get("class", []):
                    # Обработка изображений
                    yield f"![{child.get('alt', '')}]({child.get('src')})\n\n"
                else:
                    yield from get_text(child)

    joined = "".join(get_text(soup))
    return re.sub(r"\n\n+", "\n\n", joined).strip()

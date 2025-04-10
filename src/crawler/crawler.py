import sys

from .article import Article
from .jina_client import JinaClient
from .readability_extractor import ReadabilityExtractor


class Crawler:
    def crawl(self, url: str) -> Article:

        jina_client = JinaClient()
        html = jina_client.crawl(url, return_format="html")
        extractor = ReadabilityExtractor()
        article = extractor.extract_article(html)
        article.url = url
        return article


if __name__ == "__main__":
    if len(sys.argv) == 2:
        url = sys.argv[1]
    else:
        url = "https://fintel.io/zh-hant/s/br/nvdc34"
    crawler = Crawler()
    article = crawler.crawl(url)
    print(article.to_markdown())

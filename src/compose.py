"""Article composition module - creates unified article from summaries"""

import logging
from typing import Dict, List

from src.summarize import LLMClient

logger = logging.getLogger(__name__)


def compose_article(summaries: List[Dict[str, any]], provider: str = "openai") -> str:
    """Compose a unified article from multiple summaries

    Args:
        summaries: List of summary dictionaries with 'title', 'url', 'summary'
        provider: LLM provider ('openai' or 'anthropic')

    Returns:
        Markdown-formatted article (1200-1600 characters)
    """
    llm_client = LLMClient(provider=provider)

    # Build prompt with all summaries
    summaries_text = ""
    for i, summary in enumerate(summaries, 1):
        summaries_text += f"\n### 記事{i}: {summary['title']}\n"
        summaries_text += f"出典: {summary['url']}\n"
        summaries_text += "要点:\n"
        for point in summary['summary']:
            summaries_text += f"- {point}\n"

    system_prompt = """あなたは日本語テックメディアの編集長です。
複数の技術記事の要約から、一つの統合記事を作成します。

【執筆方針】
- 事実に基づき、正確な情報を提供する
- 専門用語は適切に使用し、必要に応じて簡潔に説明
- 数値、日付、固有名詞は原文に忠実に
- 推測や憶測を含む場合は明確に「〜と考えられる」「〜の可能性がある」と記載
- SEOを意識した見出し構成
- 1200〜1600文字程度

【記事構成】
1. SEO最適化されたタイトル（## 見出し）
2. 導入段落（背景・概要）
3. 主要ポイントの章立て（### 小見出し + 内容）
4. まとめ・考察
5. 参考リンク（箇条書き）"""

    user_prompt = f"""以下の要約群から、一つの統合記事を作成してください。
Markdown形式で出力し、章立てと参考リンクを含めてください。

{summaries_text}

統合記事:"""

    try:
        logger.info("Composing unified article from summaries")
        article = llm_client.generate(system_prompt, user_prompt, temperature=0.7)

        # Validate article length
        char_count = len(article)
        logger.info(f"Article composed: {char_count} characters")

        if char_count < 800:
            logger.warning(f"Article is shorter than expected: {char_count} chars")

        return article

    except Exception as e:
        logger.error(f"Failed to compose article: {e}")
        raise


def save_draft(article: str, output_file: str = "draft.md"):
    """Save article to markdown file

    Args:
        article: Markdown article text
        output_file: Output file path
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(article)
        logger.info(f"Draft saved to {output_file}")
    except IOError as e:
        logger.error(f"Failed to save draft: {e}")
        raise

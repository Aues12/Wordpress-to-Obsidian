from __future__ import annotations

import re


TURKISH_LETTER_RE = r"A-Za-zÇĞİÖŞÜçğıöşü"


def fix_wikilink_suffix_apostrophes(text: str) -> str:
    """
    Wikilink sonunda, aslında Türkçe eki başlatan apostrofu link dışına taşır.

    Examples:
      [[Başlık|Metin’]]dir -> [[Başlık|Metin]]’dir
      [[Başlık’]]den       -> [[Başlık]]’den
    """
    pattern = rf'(\[\[[^\]]+?)([\'’])\]\](?=[{TURKISH_LETTER_RE}])'
    return re.sub(pattern, r"\1]]\2", text)


def fix_emphasis_suffix_apostrophes(text: str) -> str:
    """
    Vurgu alanı sonunda, aslında Türkçe eki başlatan apostrofu vurgu dışına taşır.

    Examples:
      *Teknoloji’*nin      -> *Teknoloji*’nin
      **Teknoloji’**nin    -> **Teknoloji**’nin
      ***Teknoloji’***nin  -> ***Teknoloji***’nin
    """
    pattern = rf'(\*{{1,3}}|_{{1,3}})(.+?)([\'’])\1(?=[{TURKISH_LETTER_RE}])'
    return re.sub(pattern, r"\1\2\1\3", text)


def fix_markdown_emphasis_quotes(text: str) -> str:
    """
    Tırnakların yanlışlıkla vurgu işaretlerinin içinde kalması durumunu düzeltir.

    Examples:
      *“metin”*nı    -> “*metin*”nı
      **"metin"**in  -> "**metin**"in
      ***“metin”***e -> “***metin***”e

    Note:
    - Sadece çift tırnakları destekler: “ ” ve "
    - Tek tırnak/apostrof desteklenmez; Türkçe'de çoğunlukla ek ayırıcıdır.
    """
    pattern = r'(\*{1,3})([“"])([^“”"]+)([”"])\1'

    def repl(m: re.Match) -> str:
        stars = m.group(1)
        open_q = m.group(2)
        content = m.group(3)
        close_q = m.group(4)
        return f"{open_q}{stars}{content}{stars}{close_q}"

    return re.sub(pattern, repl, text)


def cleanup_markdown_after_wikilinks(text: str) -> str:
    """
    URL -> wikilink dönüşümünden sonra gerekli Markdown post-processing adımları.
    Sıra önemlidir.
    """
    text = fix_wikilink_suffix_apostrophes(text)
    text = fix_emphasis_suffix_apostrophes(text)
    text = fix_markdown_emphasis_quotes(text)
    
    return text

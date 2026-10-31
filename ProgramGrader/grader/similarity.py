"""同題程式相似度：忽略註解、空白與變數名稱後比較 token 序列，用來提示可能的抄襲。"""
import builtins
import functools
import io
import keyword
import re
import tokenize

MIN_TOKENS = 30  # 太短的程式寫法本來就有限，不標疑似抄襲
_KEEP = set(keyword.kwlist) | set(dir(builtins))
_SKIP = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
         tokenize.ENCODING, tokenize.ENDMARKER}


def _name(word):
    return word if word in _KEEP else 'ID'


@functools.lru_cache(maxsize=1024)  # 一題 1000 份以內都命中；長程式每份約數百 KB
def _tokens(code):
    code = code.replace('\r\n', '\n').replace('\r', '\n')
    try:
        return tuple(_name(t.string) if t.type == tokenize.NAME else t.string
                     for t in tokenize.generate_tokens(io.StringIO(code).readline) if t.type not in _SKIP)
    except (tokenize.TokenError, SyntaxError, ValueError):
        # 有語法錯誤時退回粗略切分，識別字一樣正規化，壞程式之間也比得出相似度
        # shortcut: 去註解的 regex 會誤刪字串裡 # 之後的內容；只影響語法錯誤的程式
        words = re.findall(r'\w+|[^\w\s]', re.sub(r'#[^\n]*', '', code))
        return tuple(_name(w) if w[0].isalpha() or w[0] == '_' else w for w in words)


def tokens(code):
    return list(_tokens(code))


SHINGLE = 6  # 每 6 個連續 token 一組；4 太短，通用寫法（ID = ID (）容易誤判


def _shingles(toks):
    toks = tuple(toks)
    if len(toks) <= SHINGLE:
        return frozenset([toks]) if toks else frozenset()
    return frozenset(toks[i:i + SHINGLE] for i in range(len(toks) - SHINGLE + 1))


@functools.lru_cache(maxsize=1024)  # 一題 1000 份以內都命中；長程式每份約數百 KB
def _code_shingles(code):
    return _shingles(_tokens(code))


def _dice(a, b):
    if not a or not b:
        return 0
    return round(200 * len(a & b) / (len(a) + len(b)))


def similarity(a, b):
    """兩個 token 序列的相似度 0–100：共有的 6-token 片段比例（Dice 係數），調換行序也抓得到。"""
    return _dice(_shingles(a), _shingles(b))


def comparable(a, b):
    return min(len(a), len(b)) >= MIN_TOKENS


def similar_submissions(sub, limit=5):
    """同題其他作答中最相似的幾份：[(other_sub, percent, comparable)]，可判定的排前面、相似度高的排前面。"""
    mine, mine_set = _tokens(sub.code), _code_shingles(sub.code)
    results = []
    for other in sub.question.submissions.exclude(pk=sub.pk).prefetch_related('scores'):
        ok = comparable(mine, _tokens(other.code))
        results.append((other, _dice(mine_set, _code_shingles(other.code)) if ok else 0, ok))
    results.sort(key=lambda r: (r[2], r[1]), reverse=True)
    return results[:limit]

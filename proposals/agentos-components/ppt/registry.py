"""页面登记表：页面模块按汇报顺序 import，用 @page 登记一个 fn(prs)。"""

PAGES = []


def page(fn):
    PAGES.append(fn)
    return fn

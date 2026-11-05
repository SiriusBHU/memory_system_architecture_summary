"""页面登记表：模块按汇报顺序 import，各自调用 tpl() / page() 登记页面。"""

PAGES = []


def tpl(template, **data):
    PAGES.append(("tpl", {"template": template, "data": data}))


def page(fn):
    PAGES.append(("fn", fn))
    return fn

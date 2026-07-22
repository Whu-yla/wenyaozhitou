#!/usr/bin/env python3
"""
文鳐智投 站点适配器 v2
只覆盖已知可用的公告列表页URL，其余站点保持原始URL不瞎试
"""

from urllib.parse import urlparse

# 已确认可用的站点适配器
SITE_ADAPTERS = {
    # ── 湖北 ──
    "hbggzyfwpt.cn": "https://www.hbggzyfwpt.cn/jyxx/jsgcZbgg?currentArea=&currentPage={page}&area=000&pageSize=30",
    "ggzy.hubei.gov.cn": "https://ggzy.hubei.gov.cn/hubei/jyxx/004002/004002001/?pageNo={page}",
    
    # ── 其他已确认的公共资源中心 ──
    "ggzy.hunan.gov.cn": "https://ggzy.hunan.gov.cn/trade/bulletin/index.html?type=1",
    "ggzy.guizhou.gov.cn": "https://ggzy.guizhou.gov.cn/trade/bulletin/index.html?type=1",
    "ggzy.ah.gov.cn": "https://ggzy.ah.gov.cn/jyxx/002001/002001001/?pageNo={page}",
    
    # ── 国网 ── (JS渲染，标记)
    "ecp.sgcc.com.cn": None,  # JS_REQUIRED
    "sgcc.com.cn": None,
    
    # ── 华能 ──
    "chnzb.cn": "https://www.chnzb.cn/search/?q=&type=zbgg&page={page}",
    
    # ── 中国招标投标公共服务平台 ──
    "cebpubservice.com": "https://bulletin.cebpubservice.com/biddingBulletin/2024-01-01/{page}.html",
    
    # ── 采购与招标网 ──
    "chinabidding.com.cn": "https://www.chinabidding.com.cn/search/searchzbw/searchpro?page={page}",
}

# JS渲染站点（requests无法获取，暂跳过）
JS_SITES = {"ecp.sgcc.com.cn", "sgcc.com.cn", "ecp.sgcc"}


def get_listing_urls(site_url: str, max_pages: int = 2) -> list[str]:
    """获取公告列表页URL列表。已适配站点用专用URL，其余用原始URL。"""
    domain = urlparse(site_url).netloc.lower()
    
    # JS站点跳过
    for js in JS_SITES:
        if js in domain:
            return [site_url]  # 返回原URL，标记为JS但不跳过
    
    # 匹配已知适配器
    for key, template in SITE_ADAPTERS.items():
        if key in domain:
            if template is None:  # JS站点
                return [site_url]
            if "{page}" in template:
                return [template.replace("{page}", str(p)) for p in range(1, max_pages + 1)]
            return [template]
    
    return [site_url]


def get_listing_url(site_url: str, page: int = 1) -> str:
    """单个列表页URL"""
    urls = get_listing_urls(site_url, max_pages=1)
    return urls[0] if urls else site_url


def needs_js_render(site_url: str) -> bool:
    domain = urlparse(site_url).netloc.lower()
    return any(js in domain for js in JS_SITES)


if __name__ == "__main__":
    tests = [
        "https://www.hbggzyfwpt.cn/",
        "https://ecp.sgcc.com.cn/",
        "https://www.chnzb.cn/",
        "https://ggzy.hunan.gov.cn/",
        "https://www.chinabidding.com.cn/",
        "https://some-unknown-site.com/",
    ]
    for url in tests:
        list_url = get_listing_url(url)
        js = "🔴JS" if needs_js_render(url) else "🟢"
        print(f"{js} {url[:50]} → {list_url[:70]}")

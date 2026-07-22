#!/usr/bin/env python3
"""
文鳐智投 Chromium JS渲染批量采集
攻克需要JS的招标平台：浙能、国网、南网、能建等
"""
import subprocess, re, json, sys, time, sqlite3, hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

BASE_DIR = Path("/root/.hermes/profiles/wenyaozhitou")
sys.path.insert(0, str(BASE_DIR / "scripts"))

from relevance_scorer import score_items

# ═══ L1 页面类型判别器 — 识别非公告页面 ═══
PAGE_SIGNALS_REJECT = [
    # 平台欢迎/首页信号
    '欢迎来到', '欢迎您', '欢迎光临', 'V1.0欢迎您',
    '设为首页', '收藏此页', '平台首页', '网站首页',
    # 导航/面包屑（没有实际公告内容）
    '您当前访问的是', '访问正式平台', '请点击 https://',
    '电子采购平台首页', '平台操作流程', 'CA办理',
    # 非公告页面
    '易招标-首页', '产品与服务', '成功案例',
    '中国招标投标协会', '年会报道', '年会召开',
    # 企业宣传/文章
    '三十而立', '岁月答卷', '三峡小微', '小说阅读',
    # 空列表/无内容
    '暂无数据', '没有找到', '无相关公告',
]

def is_valid_notice_page(text, title=''):
    """检查页面是否为真实公告详情页，而非平台首页/导航/宣传页"""
    combined = (title + ' ' + text)[:2000]
    
    # 1. 必须足够长
    if len(text) < 100:
        return False
    
    # 2. 必须含公告核心词
    notice_keywords = ['招标', '中标', '采购', '公告', '公示', '投标', '项目']
    if not any(kw in combined for kw in notice_keywords):
        return False
    
    # 3. 拒绝平台导航/欢迎/首页信号
    rejection_count = 0
    for signal in PAGE_SIGNALS_REJECT:
        if signal in combined:
            rejection_count += 1
    # 3个以上拒绝信号 → 判定为非公告页
    if rejection_count >= 3:
        return False
    
    # 4. 拒绝纯导航（标题太短且含平台名）
    if len(title) < 15 and any(kw in title for kw in ['平台', '首页', '系统', '易招标']):
        return False
    
    return True

CHROMIUM = "/snap/bin/chromium"
CHROMIUM_ARGS = "--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage --virtual-time-budget=20000 --dump-dom"

# JS渲染目标：最重要的能源招标平台
JS_TARGETS = [
    ("浙能集团招标公告", "https://zsrm.zjenergy.com.cn/zjnycms/category/bulletinListNew.html?dates=300&categoryId=2&tenderMethod=01&page=1"),
    ("浙能集团中标公告", "https://zsrm.zjenergy.com.cn/zjnycms/category/bulletinListNew.html?dates=300&categoryId=5&tenderMethod=01&page=1"),
    ("中国能建招标公告", "https://ec.ceec.net.cn/HomeInfo/ZhaoBiaoGG_More.aspx"),
    ("中国能建中标公示", "https://ec.ceec.net.cn/HomeInfo/winDid_More.aspx"),
    ("南方电网招标公告", "http://www.bidding.csg.cn/zbcg/index.jhtml"),
    ("国家电投招标公告", "https://ebid.espic.com.cn/sdny_bulletin/"),
    ("长江电力招标", "https://ecn.cypc.com.cn/getBidBulletinPublic?p=1"),
    ("中国船舶招标", "https://csscbidding.com/jyxx/003001/trade_info.html"),
    ("内蒙古电力招标", "http://impc.e-bidding.org/nmcms/category/bulletinList.html?dates=300&categoryId=88&page=1"),
    ("深圳能源招标", "https://zb.sec.com.cn/zbggs/index.jhtml"),
    ("深圳能源结果公告", "https://zb.sec.com.cn/jggs/index.jhtml"),
    ("国电南自招标", "https://srm.sac-china.com/oauth/public/default/bid_notice.html"),
]

def chromium_fetch(url, timeout=25):
    try:
        result = subprocess.run(
            [CHROMIUM] + CHROMIUM_ARGS.split() + [url],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0 and result.stdout and len(result.stdout) > 500:
            return result.stdout
    except:
        pass
    return None

def extract_detail_links(html, base_url):
    """从渲染后的HTML提取详情链接"""
    links = set()
    # 找所有a标签href
    for m in re.finditer(r'<a[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>', html, re.I):
        href = m.group(1)
        text_match = re.search(r'>([^<]*)</a>', html[m.start():m.start()+500])
        text = text_match.group(1) if text_match else ''
        combined = (href + text).lower()
        
        if any(kw in combined for kw in ['detail', 'bulletin', 'zbgg', 'zbxx', 'cggg',
                                           'notice', 'announce', 'tender', 'bid',
                                           'view', 'info', 'content', 'show',
                                           '招标', '中标', '公告', '详情', '公示']):
            if any(skip in combined for skip in ['login', 'register', 'more', 'page=']):
                continue
            full = urljoin(base_url, href)
            if not full.startswith('http'):
                continue
            # 过滤导航/索引页（如 /zbggs/index.jhtml /zbgg/index.jhtml）
            if re.search(r'/index(?:[_\u4e00-\u9fff])?(?:_?\d+)?\.\w+$', full):
                continue
            links.add(full)
    return list(links)[:30]

def fetch_detail_text(url):
    """用requests获取详情页文本+标题（详情页通常不需要JS）"""
    import requests
    import urllib3
    urllib3.disable_warnings()
    try:
        r = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }, timeout=15, verify=False)
        if r.status_code >= 400 or len(r.text) < 300:
            return None, None
        # 尝试多种编码
        for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
            try:
                r.encoding = enc
                if any(c in r.text for c in '招标中标公告采购'):
                    break
            except:
                continue
        # 提取文本：优先 .Content 主内容区（深圳能源等平台）
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 标题：优先 h1，其次 .Content 首行
        h1_title = ''
        h1_tag = soup.find('h1')
        if h1_tag:
            h1_title = h1_tag.get_text(strip=True)[:200]
        
        content_div = soup.find('div', class_='Content')
        if content_div:
            text = re.sub(r'\s+', ' ', content_div.get_text()).strip()
            text = text[:3000] if len(text) > 80 else None
        else:
            # 兜底：全页文本
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            text = re.sub(r'\s+', ' ', soup.get_text()).strip()[:3000]
        return text, h1_title
    except:
        return None, None

def main():
    print(f"[{datetime.now():%H:%M:%S}] Chromium批量采集启动")
    
    conn = sqlite3.connect(str(BASE_DIR / 'data' / 'bidding.db'))
    all_items = []
    
    for name, url in JS_TARGETS:
        print(f"\n── {name} ──")
        html = chromium_fetch(url)
        if not html:
            print(f"  ❌ Chromium渲染失败")
            continue
        
        print(f"  渲染成功: {len(html)} chars")
        links = extract_detail_links(html, url)
        print(f"  发现 {len(links)} 个详情链接")
        
        site_items = 0
        site_rejected = 0
        for dl in links[:10]:
            text, h1_title = fetch_detail_text(dl)
            if not text or len(text) < 50:
                continue
            
            # 尝试提取标题：优先 h1
            title = h1_title if h1_title else ''
            if not title:
                for line in text.split('\n'):
                    line = line.strip()
                    if 10 < len(line) < 150 and any(kw in line for kw in ['招标','中标','采购','公告','项目']):
                        title = line
                        break
            if not title:
                title = text[:100]
            # 清理模板占位符
            title = re.sub(r'@\S+@', '', title).strip()
            
            # ★ L1 页面类型判别 — 拒绝平台首页/导航/欢迎页
            if not is_valid_notice_page(text, title):
                site_rejected += 1
                print(f"    🚫 L1拒绝: {title[:50]}")
                continue
            
            item = {
                'title': title,
                'content': text[:500],
                'source': name,
                'source_url': dl,
                'notice_type': 'bidding',
                'publish_date': '',
                'procurement_owner': '',
                'raw_text': text,
            }
            all_items.append(item)
            site_items += 1
            print(f"    → {title[:60]}")
        
        print(f"  本平台采集 {site_items} 条，L1拒绝 {site_rejected} 条")
        
        # 每2个平台跑一次评分
        if len(all_items) >= 30:
            _score_batch(conn, all_items)
            all_items = []
    
    if all_items:
        _score_batch(conn, all_items)
    
    total = conn.execute("SELECT count(*) FROM bidding_notices").fetchone()[0]
    print(f"\n库内总计: {total}")
    conn.close()

def _score_batch(conn, items):
    scored = score_items(items)
    for s in scored:
        h = hashlib.md5((s.get('source_url','') or '').encode()).hexdigest()
        try:
            conn.execute("""
                INSERT OR IGNORE INTO bidding_notices
                (title, url, source_site, notice_type, publish_date, fetch_date,
                 content_summary, is_new, unique_hash, relevance_score,
                 procurement_owner, region, province, category)
                VALUES (?,?,?,?,?,?,?,1,?,?,?,?,?,?)
            """, (
                (s.get('title','') or '')[:200],
                (s.get('source_url','') or '')[:500],
                (s.get('source','') or '')[:200],
                'bidding', s.get('publish_date',''),
                datetime.now().isoformat(),
                (s.get('content','') or s.get('raw_text',''))[:2000],
                h, s.get('relevance_score', 0),
                s.get('procurement_owner','')[:200],
                s.get('region',''), s.get('province',''),
                s.get('category',''),
            ))
        except Exception as e:
            print(f"  ⚠️ 入库失败: {e}")
    conn.commit()
    if scored:
        print(f"  → 评分入库 {len(scored)} 条")

if __name__ == '__main__':
    main()

# Polish Script Idempotency & Injection Guards

## Version Marker Pattern (V1.33+)

Every ENHANCE_CSS injection in `polish_report.py` MUST use a version marker:

```python
ENHANCE_CSS = '''
... CSS rules ...
}/* V1.33-enhance */'''
```

Guard:
```python
if 'V1.33-enhance' not in html:
    html = html.replace('</style>', ENHANCE_CSS + '\n</style>')
    modified = True
```

## Why This Matters

| Approach | If feature is rolled back | If feature is renamed |
|:--|:--|:--|
| Guard on feature class (e.g. `'more-filters-toggle'`) | Guard permanently true → CSS re-injected every polish run → duplicate `@media` blocks | Guard breaks differently depending on what changed |
| Guard on version marker (`'V1.33-enhance'`) | Marker stays → guard works. Marker removed → guard adds one fresh copy with new marker. | Not applicable — marker is independent of feature content |

## Nightmare Scenario (actually happened)

1. User approved "更多筛选" collapsible feature
2. ENHANCE_CSS guard: `if 'more-filters-toggle' not in html`
3. User rejected the feature → code rolled back → `more-filters-toggle` class removed from HTML
4. Guard now permanently TRUE → ENHANCE_CSS injected every polish run
5. 7 duplicate `@media(max-width:768px)` blocks accumulated
6. Mobile layout completely broken
7. Required manual cleanup of duplicates + guard fix

## File Permission Safety

```bash
# WRONG — kills directory x-bits
chmod 644 /var/www/html/bidding/*

# RIGHT — files only, directories preserved
find /var/www/html/bidding -maxdepth 1 -type f -exec chmod 644 {} \;
chmod 755 /var/www/html/bidding/img /var/www/html/bidding/img_gen
```

Nginx log check: `tail /var/log/nginx/error.log | grep "Permission denied"`
If `stat() ... failed (13: Permission denied)` → directory missing `x` bit → `chmod 755`.

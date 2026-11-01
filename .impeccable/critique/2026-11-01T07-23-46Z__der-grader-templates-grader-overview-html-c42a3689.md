---
target: dashboard (成績總覽)
total_score: 28
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 0
target_identity: "file:/Users/yehweipingrubi/Desktop/Django/ProgramGrader/ProgramGrader/grader/templates/grader/overview.html"
target_fingerprint: "sha256:83655539b9d2b0b74f1389093f1a944aa5428b4d28b7e7edf594b82d64fd422d"
target_path: /Users/yehweipingrubi/Desktop/Django/ProgramGrader/ProgramGrader/grader/templates/grader/overview.html
timestamp: 2026-11-01T07-23-46Z
slug: der-grader-templates-grader-overview-html-c42a3689
---
Method: dual-agent (A: design review · B: detector + browser)

## Design Health Score: 28/40 (Good) — same total as last run, different composition (prior P1 and P2s resolved)
| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 3 | 篩選後沒有「顯示 N/120 位」；搜尋自動取消篩選無說明 |
| 2 | Match System / Real World | 3 | 「淡色總分* 尚未改完」稍嫌暗號 |
| 3 | User Control and Freedom | 3 | 搜尋標示無法清除 |
| 4 | Consistency and Standards | 3 | 搜尋列藍底蓋掉待改/需複查底色 |
| 5 | Error Prevention | 3 | 匯出防呆完整 |
| 6 | Recognition Rather Than Recall | 3 | 各題進度配分只在 tooltip |
| 7 | Flexibility and Efficiency | 2 | 無搜尋快捷鍵、無方向鍵、搜尋只接受完整學號、無排序 |
| 8 | Aesthetic and Minimalist | 3 | 中途總分欄幾乎全是淡色*；返回與麵包屑重複 |
| 9 | Error Recovery | 2 | 「找不到」不提示部分符合的學號 |
| 10 | Help and Documentation | 3 | 未說明需複查的來源 |

## Design Specificity
資訊架構與狀態編碼專屬；視覺為通用後台（Operate 可接受）。Detector：CLI 0（{% static %} 限制）；URL 掃描 3 頁 0；overlay 4 視圖 0；上輪 4 筆 low-contrast 全部消失。

## Priority Issues
1. [P2] 雙層捲動陷阱仍在（首屏滾輪捲表格內層，表格底緣與水平捲軸在首屏外）→ /impeccable layout
2. [P2] 中途「只看還沒改完的學生」幾乎無效（119/120），總分 * 飽和；無顯示筆數 → /impeccable distill + harden
3. [P2] 搜尋邊角：自動取消篩選無訊息、找不到殘留、不支援部分學號、標示清不掉且蓋掉狀態底色 → /impeccable harden
4. [P3] 12 個等權重「繼續批改」，第一名未升級為建議起點；配分只在 tooltip；390 寬進度區 1016px → /impeccable polish
5. [P3] 需複查只說後果不說原因 → /impeccable clarify

## Persona Red Flags
- Alex：無 / 快捷鍵、無方向鍵、1440 個 Tab 停點、無排序、搜尋需完整學號。
- Sam：篩選切換無播報與筆數；篩選被悄悄改掉。
- 13 吋多班合改助教：首屏 9 列（改善），但第一下滾輪捲內層；未交任何題的學生不在名單。

## Questions to Consider
- 依題批改時，「學生沒改完」是對的篩選角度嗎？
- 批改中途成績表需要佔半頁嗎？
- 畫面有 * 但 CSV 沒有狀態欄，Excel 裡部分總分像定案？

## Resolved since 28/40 run
P1 矩陣首屏外；需複查分數說明；用詞統一；進度對齊；排序；只看待改；同名連結；部分總分淡色+滿分；aria-current；390 進度換行；搜尋失敗位移；4/4 對比問題。

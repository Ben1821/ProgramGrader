---
target: dashboard (成績總覽)
total_score: 28
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 1
target_identity: "file:/Users/yehweipingrubi/Desktop/Django/ProgramGrader/ProgramGrader/grader/templates/grader/overview.html"
target_fingerprint: "sha256:51233e9afe7f72105ee49c552832bd279a278362d02e7bdc7f6261f13f05dfd9"
target_path: /Users/yehweipingrubi/Desktop/Django/ProgramGrader/ProgramGrader/grader/templates/grader/overview.html
timestamp: 2026-11-01T06-56-58Z
slug: der-grader-templates-grader-overview-html-c42a3689
---
Method: dual-agent (A: design review · B: detector + browser)

## Design Health Score: 28/40 (Good)
| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 3 | 整體與各題進度清楚；需複查格分數只含測資分未說明；導覽無目前位置 |
| 2 | Match System / Real World | 3 | 用語貼近；匯出警語「這些題目」應為「這些份」 |
| 3 | User Control and Freedom | 3 | 唯讀頁；搜尋標示無法清除 |
| 4 | Consistency and Standards | 2 | 已改/已完成、待改/待人工評分 混用；進度表數字欄表頭與數字對不齊 |
| 5 | Error Prevention | 3 | 匯出防呆到位；部分總分仍粗體 |
| 6 | Recognition Rather Than Recall | 3 | 表頭/學號/總分固定、圖例緊貼、datalist |
| 7 | Flexibility and Efficiency | 2 | 無只看待改、無依待改排序、無跨題下一份待改 |
| 8 | Aesthetic and Minimalist | 3 | 進度區在 1280×800 佔 465px，矩陣從 y=681 開始 |
| 9 | Error Recovery | 3 | 需複查已分開；未說明退回原因 |
| 10 | Help and Documentation | 3 | 圖例、匯出說明足夠 |

## Design Specificity
流程專屬（進度→匯出→跳學號→矩陣；形狀+顏色狀態符號），視覺為通用後台但適合 Operate。Detector：模板 CLI 0（{% static %} 漏報）；URL/overlay：總覽只剩 a.back 4.4:1；上次 9 筆中 7 筆已消失；grade-similar 新增 3 筆（疑似抄襲列 #fdf1ef 底、span.ok 4.1:1）。

## Priority Issues
1. [P1] 矩陣被推到首屏外 + 雙層捲動陷阱（1280×800 矩陣 y=681，滾輪捲內層不捲頁面）→ /impeccable layout
2. [P2] 需複查格分數只含測資分但未說明 → /impeccable clarify
3. [P2] 狀態詞彙不一致（已改/已完成、待改/待人工評分）、進度表對齊 → /impeccable polish
4. [P2] 看不出該先改哪題、無只看待改；12 個同名「繼續批改」→ /impeccable layout + harden
5. [P3] 部分總分像定案；* 只有 title；無滿分 → /impeccable typeset

## Persona Red Flags
- Alex：無篩選/排序、無跨題下一份待改、矩陣無方向鍵、搜尋不支援部分學號。
- Sam：12 個同名連結、* 無 sr-only、無 aria-current。
- 期末合併班助教（13 吋）：首屏不見矩陣且第一次滾輪落進內層；需複查分數誤導；一題都沒交的學生不在名單。

## Minor Observations
搜尋失敗訊息造成圖例位移；搜尋標示蓋掉狀態底色；390 寬進度表需橫捲無提示；a.back 4.4:1；grade 頁 span.ok 4.1:1、疑似抄襲列文字 4.3–4.4:1。

## Resolved since 23/40 run
大班版面、進度彙總、匯出防呆、需複查區分、表格語意、底色對比、emoji、匯出移位、圖例上移；7/9 對比問題。

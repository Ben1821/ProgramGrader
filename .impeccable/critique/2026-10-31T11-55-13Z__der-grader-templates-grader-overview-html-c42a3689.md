---
target: dashboard (成績總覽)
total_score: 23
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/Users/yehweipingrubi/Desktop/Django/ProgramGrader/ProgramGrader/grader/templates/grader/overview.html"
target_fingerprint: "sha256:3ce44cf472dfe50e6a3041ffc88895d0044a623d1db6d81c1675304c70a4de5b"
target_path: /Users/yehweipingrubi/Desktop/Django/ProgramGrader/ProgramGrader/grader/templates/grader/overview.html
timestamp: 2026-10-31T11-55-13Z
slug: der-grader-templates-grader-overview-html-c42a3689
---
Method: dual-agent (A: design review · B: detector + browser)

## Design Health Score: 23/40 (Acceptable)
| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 2 | 每格有狀態，但沒有總體進度（各題待改數、完成率） |
| 2 | Match System / Real World | 3 | 用語貼近助教；`*`、✋ emoji 偏隨意 |
| 3 | User Control and Freedom | 3 | 唯讀頁，進出容易 |
| 4 | Consistency and Standards | 2 | 數字置中、學號字體與批改頁不同；匯出是導覽連結而非按鈕 |
| 5 | Error Prevention | 2 | 有待改仍可直接匯出 CSV；部分總分用粗體像最終成績 |
| 6 | Recognition Rather Than Recall | 2 | 表頭會捲走；圖例在頁尾 |
| 7 | Flexibility and Efficiency | 2 | 點題號續改很好；無篩選、跳學號、全域下一份待改 |
| 8 | Aesthetic and Minimalist | 2 | 上百格重複「待改」、全是同權重藍色連結 |
| 9 | Error Recovery | 2 | 因設定變更退回的待改格與從未改過的無法區分 |
| 10 | Help and Documentation | 3 | 頂部提示+圖例對熟手足夠 |

## Design Specificity
流程專屬（學生×題目矩陣、點題號續改、與 CSV 同源），視覺為通用後台骨架。Detector：模板 CLI 0（`{% static %}` 讀不到 CSS，漏報）；URL 掃描 9 筆 low-contrast advisory（4.2–4.46:1，#2f6fdb / #6b7280 在淺底）。

## Priority Issues
1. [P1] 版面撐不住大型班級：無 sticky 表頭/學號欄，1280 寬「待改」斷行，120 人約 7,600px 高，>14 題超出寬度。→ /impeccable adapt
2. [P1] 沒有進度彙總與主要下一步（繼續批改、各題待改數、只看待改）。→ /impeccable layout
3. [P1] 匯出不提醒尚有待改，部分總分看似最終成績。→ /impeccable harden
4. [P2] 待改/完成底色對比僅 1.02:1、全藍連結、數字置中比例字。→ /impeccable colorize + typeset
5. [P2] 表格語意與對比：無 thead/th scope、連結名稱重複、多處對比 4.2–4.46:1。→ /impeccable harden

## Persona Red Flags
- Alex：無鍵盤捷徑、無篩選/跳學號、無跨題下一份待改。
- Sam：無表頭語意、連結名稱重複、emoji 被唸出、對比略低於 AA、focus 不明顯。
- 期末合併班助教（180×10、13 吋）：表頭捲走、找不到卡住的題、匯出前無警告、退回複查的格子無法辨識。

## Minor Observations
導覽缺目前位置；回首頁三條路；.hint 14px 與 muted 15px 不一致；總分未顯示滿分；未交任何題的學生不會出現；單題時右側大片空白；favicon 404。

## Questions to Consider
- 總覽主角應是矩陣，還是「還剩什麼要做」？
- 部分分數該不該看起來像分數？
- 學生數無上限時，一人一列全攤開還是對的單位嗎？

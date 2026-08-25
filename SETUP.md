# 在一台常开机的电脑上设定每日自动股市报告

这份文件是给「在那台常开机的电脑上打开的 Claude Code」看的操作手册。使用者会说类似「读 SETUP.md 并照着做」，照下面步骤执行即可，不需要再回来问使用者细节（除非真的卡住）。

## 背景

这套系统会每天自动：
1. 抓台股/美股行情、新闻
2. 分析使用者的持仓
3. AI 排名选出 Top 10 推荐股票
4. 用 LINE 把报告推播给使用者

之前尝试用 Claude 的云端 routine 执行，但云端沙盒的对外网路有白名单限制，连不到 Yahoo Finance / Google News / LINE API，所以改成在使用者自己一台常开机的电脑上，用 Claude Code 的本机 scheduled task 功能执行（本机网路没有这个限制）。

## 步骤

1. **确认这台电脑本身网路正常**，能连到一般网站（不像云端沙盒有白名单限制）。

2. **确认这个 repo 已经 clone 到本机**，路径记下来（例如 `C:\Users\<user>\Documents\Stock_Agent`）。如果这份 SETUP.md 是你正在读的档案，代表已经 clone 好了，你现在的工作目录就是它。

3. **确认已连接 Google Drive MCP 连接器**（跟建立这个系统时使用的是同一个 Anthropic 帐号，连接器通常是帐号层级，理论上不需要重新连接；如果发现读不到档案，才需要使用者去 claude.ai/customize/connectors 重新连接）。

4. **取得敏感资料并写入本机档案**（这两个档案绝对不能 commit、push 或输出/回传内容）：
   - 用 Google Drive 连接器的 `read_file_content`（或 `download_file_content`）读取 LINE token 档案，fileId = `1wRfJPq3YJUMBZSHJvTEHBWVTPqguKYj2`，内容（去除头尾空白）写入本机 `.env`：`LINE_CHANNEL_ACCESS_TOKEN=<内容>`
   - 持仓资料是 Google Sheet，fileId = `1m3kc3QRDuFH_gYWeUNBy4MbOaafLeHgkWEnu4NMqJyo`。用 `download_file_content`（exportMimeType 设为 `text/csv`）取得内容，回传的 `content` 是 base64，要先 base64 解码成文字，再写入本机 `portfolio.csv`

5. **安装 Python 相依套件**：`pip install -r requirements.txt`

6. **跑一次测试**，确认整条链路在这台机器上真的能跑通（不像云端沙盒那样被挡）：
   - `python fetch_market.py tw`（应该要能抓到 40+ 档资料，不是 0 档）
   - `python fetch_news.py tw`（macro_news 跟 stock_news 应该要有实际内容，不是全部是空的）
   - `python send_line.py "测试：常开机排程设定测试讯息"`（使用者应该会在 LINE 收到）
   若有任何一步跟云端沙盒当时一样被挡（网路连不出去），要如实告诉使用者，不要假装成功。

7. **确认测试都通过后，建立三个本机 scheduled task**（用 `create_scheduled_task` 工具，cron 是这台机器的本地时间）：

   **台股早报**：
   - taskId: `tw-stock-morning-report`
   - cronExpression: `30 8 * * 1-5`（周一至周五 08:30，台股开盘前半小时）
   - description: 台股每日早报
   - prompt（把 `<REPO_PATH>` 换成这个 repo 在本机的实际路径）：
     ```
     cd 到 <REPO_PATH>，先执行 git pull 取得最新脚本。然后严格照着这个目录下 RUN_TW.md 的每一步执行（step 0 用 Google Drive 连接器读取 LINE token 和持仓资料写入本机 .env 与 portfolio.csv；最后一步无论如何都要送出一则 LINE 讯息，绝不能默默失败）。绝对不能 commit、push 或输出/回传 token 与持仓内容。
     ```

   **美股晚报（夏令 EDT）**：
   - taskId: `us-stock-evening-report-edt`
   - cronExpression: `0 21 * * 1-5`（周一至周五 21:00）
   - description: 美股每日晚报（夏令）
   - prompt：
     ```
     这是美股晚报（夏令 EDT 检查版）。第一步：先判断美东时间现在是夏令(EDT, UTC-4)还是冬令(EST, UTC-5)，例如执行 python3 -c "import datetime, zoneinfo; print(datetime.datetime.now(zoneinfo.ZoneInfo('America/New_York')).utcoffset())"。如果结果是 -5:00:00（冬令），代表现在不该由这个任务处理，什么都不要做、也不要发送任何讯息（有另一个冬令版本的任务负责）。只有结果是 -4:00:00（夏令）才继续。继续的话：cd 到 <REPO_PATH>，先执行 git pull，然后严格照着 RUN_US.md 的每一步执行（step 0 用 Google Drive 连接器读取 LINE token 和持仓资料写入本机 .env 与 portfolio.csv；最后一步无论如何都要送出一则 LINE 讯息，绝不能默默失败，但上面季节不符要跳过的情况例外，那种情况保持完全安静）。绝对不能 commit、push 或输出/回传 token 与持仓内容。
     ```

   **美股晚报（冬令 EST）**：
   - taskId: `us-stock-evening-report-est`
   - cronExpression: `0 22 * * 1-5`（周一至周五 22:00）
   - description: 美股每日晚报（冬令）
   - prompt：跟夏令版几乎一样，但条件相反——只有美东时间是 **-5:00:00（冬令）** 才继续执行 RUN_US.md，是 -4:00:00（夏令）就什么都不做、不发讯息。

8. **完成后跟使用者报告**：三个 scheduled task 建好了没、刚才的手动测试有没有真的收到 LINE 讯息、这台电脑需要保持这个 Claude Code App 处于开启状态 scheduled task 才会准时执行（这点务必提醒使用者）。

## 重要提醒

- `.env` 和 `portfolio.csv` 只能留在本机，绝对不能进 git（repo 的 `.gitignore` 已经排除，不要手动 `git add -f` 覆盖这个规则）
- 如果这台电脑关机或 Claude Code App 没开，scheduled task 不会准时触发，会等下次开启才补跑——这是本机排程的已知限制，跟使用者说清楚

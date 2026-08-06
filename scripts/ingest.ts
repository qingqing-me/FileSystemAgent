/**
 * Ingestion Script — Crawl GXU file system and feed into the RAG backend.
 *
 * This version filters documents by title BEFORE sending to the backend:
 * transient notices (停电/施工/名单/处分决定...) are skipped, only
 * long-term policies and regulations are indexed.
 *
 * Usage:
 *   cd scripts && npm install && npm run ingest
 *
 * Environment variables:
 *   WJXT_USERNAME  — student ID
 *   WJXT_PASSWORD  — password
 *   BACKEND_URL    — FastAPI backend URL (default: http://localhost:8000)
 */

import { WjxtClient } from "gxu-wjxt";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const USERNAME = process.env.WJXT_USERNAME || "";
const PASSWORD = process.env.WJXT_PASSWORD || "";

if (!USERNAME || !PASSWORD) {
  console.error("❌ 请设置环境变量: WJXT_USERNAME 和 WJXT_PASSWORD");
  process.exit(1);
}

// ============ 标题过滤规则（与 cleanup_docs.py 一致） ============

// 明确是长期有效政策 → 强制保留
const KEEP_PATTERNS = [
  /实施办法/,
  /管理办法/,
  /管理规定/,
  /工作办法/,
  /条例/,
  /制度/,
  /规定$/,
  /办法$/,
  /细则/,
  /指导意见/,
  /实施方案/,
  /评审办法/,
  /评定办法/,
  /推荐.*免试.*研究生/,
  /推免/,
  /保研/,
  /培养方案/,
  /教学计划/,
  /校历/,
  /学籍.*规定/,
  /学位.*办法/,
  /导师制/,
  /毕业论文.*规定/,
  /创新创业.*学分/,
  /交流生.*办法/,
  /本研一体化/,
  /学生资助政策/,
  /国家奖助学金.*评审管理/,
  /学生奖励办法/,
  /学生处分规定/,
  /转专业.*办法/,
  /转专业.*通知$/,
  /专业分流.*通知/,
  /辅修.*办法/,
  /微专业/,
  /免试认定/,
];

// 临时/一次性文件 → 丢弃
const DISCARD_PATTERNS = [
  // 基建后勤临时通知
  /停电/, /停水/, /施工/, /消杀/, /病虫害/, /道路封闭/,
  /临时(占用|管控|封闭)/, /倒闸/, /错峰用电/, /限制使用/,
  /短时停电/, /停气/, /交通管制/, /占道/, /封闭道路/,
  /封闭.*道路/, /路灯运行/, /空调(清洗|消毒|限)/, /物业费/,
  /封闭.*(路段|车道|道路)/, /临时封闭/,

  // 特定考试的准考证/报名（一次性考务）
  /(四、六级|四六级)考试.*(准考证|报名|听力|测试)/,
  /英语四、六级.*(准考证|报名)/,

  // 征文、作品征集
  /征文/,
  /关于征集.*作品/,
  /关于.*作品征集/,

  // 具体选拔运动员
  /关于选拔.*运动员/,

  // 针对具体人的行政决定
  /关于准予.*(退学|毕业|结业|自动退学)的决定/,
  /关于授予.*(学士|硕士|博士)学位的决定/,
  /关于给予.*退学处理的决定/,
  /关于给予.*(记过|严重警告|警告|留校察看|开除学籍)处分的决定/,
  /关于解除.*(记过|严重警告|警告|留校察看|开除学籍)处分的决定/,
  /关于给予.*(记过|严重警告|警告|留校察看|开除学籍)的处分/,
  /关于解除.*处分的决定/,
  /关于撤销.*处分的决定/,
  /关于同意办理.*(复学|休学|保留学籍)的决定/,
  /关于同意办理.*的决定/,
  /关于表彰.*的决定/,
  /关于聘任.*的通知/,
  /关于.*换届任职/,
  /关于公布.*名单/,
  /关于公布.*获奖名单/,
  /关于.*评选结果的公示/,
  /关于.*推荐名单/,
  /关于.*拟推荐/,
  /关于.*名单的公示/,

  // 宿舍日常通报
  /学生宿舍未按时熄灯/,
  /学生宿舍安全.*抽检/,
  /宿舍.*情况通报/,

  // 转发
  /转发.*的通知$/,

  // 临时活动、比赛
  /关于举办.*大赛/,
  /关于举办.*比赛/,
  /关于举行.*比赛/,
  /关于举办.*活动/,
  /关于组织参加.*大赛/,
  /关于组织参加.*竞赛/,
  /关于组织.*参赛/,

  // 党建通讯简报
  /党建通讯/,
  /简报/,

  // 节假日调课
  /关于调整.*放假.*教学安排/,
  /关于.*元旦.*放假/,
  /关于.*劳动节.*放假/,

  // 讲座培训
  /关于举办.*讲座/,
  /关于举办.*培训/,
  /关于举办.*报告会/,
  /关于举办.*训练营/,

  // 学期考务、晚自习
  /关于.*学期.*考试安排/,
  /关于.*学期.*晚自习/,

  // 用能
  /用能(巡查|抽查)/,
  /用电情况/,

  // 废弃车、烟花爆竹
  /废弃车/,
  /烟花爆竹/,

  // 项目名单/立项
  /关于公布.*项目.*名单/,
  /关于公布.*立项/,

  // 团组织人事
  /关于同意共青团.*选举结果/,
  /关于.*团委.*更名/,

  // 校运会单项
  /关于举行.*校运会/,
  /关于举行.*篮球赛/,
  /关于举行.*气排球/,
  /关于举行.*足球/,
  /关于举行.*网球/,
  /关于举行.*羽毛球/,
  /关于举行.*跳绳/,

  // 作品征集
  /关于征集.*作品/,
  /关于.*作品征集/,

  // 毕业生离校/办理
  /关于.*毕业生.*办理/,
  /关于.*毕业.*离校/,

  // 军训征兵
  /关于.*征兵/,

  // 新生入馆教育
  /新生.*入馆教育/,

  // 团评优名单
  /关于表彰.*共青团/,
  /关于表彰.*团员/,
  /关于表彰.*志愿/,

  // 奖学金/助学金具体名单公示
  /(奖学金|助学金|资助).*评选结果公示/,
  /(奖学金|助学金|资助).*推荐名单公示/,
  /关于颁发.*奖学金的决定$/,
  /关于颁发.*助学金的决定$/,
  /关于颁发.*基金的决定$/,
];

function shouldKeep(title: string): { keep: boolean; reason: string } {
  for (const p of KEEP_PATTERNS) {
    if (p.test(title)) return { keep: true, reason: `KEEP: ${p.source}` };
  }
  for (const p of DISCARD_PATTERNS) {
    if (p.test(title)) return { keep: false, reason: `DISCARD: ${p.source}` };
  }
  // 默认保留（保守）
  return { keep: true, reason: "KEEP: default" };
}

async function sendToBackend(file: {
  id: number;
  title: string;
  department: string;
  date: string;
  rawHtml: string;
}) {
  const body = {
    file_id: file.id,
    title: file.title,
    department: file.department,
    date: file.date,
    raw_html: file.rawHtml,
  };

  const res = await fetch(`${BACKEND_URL}/api/admin/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    console.error(`  ⚠️  后端错误 ${res.status}: ${text.slice(0, 200)}`);
    return false;
  }

  const data = (await res.json()) as { message?: string };
  console.log(`  ✅ ${data.message}`);
  return true;
}

async function main() {
  console.log("🚀 开始爬取广西大学文件系统（已启用过滤）...\n");

  const client = new WjxtClient({ username: USERNAME, password: PASSWORD });
  const loggedIn = await client.login();
  if (!loggedIn) {
    console.error("❌ 登录失败，请检查用户名和密码");
    process.exit(1);
  }
  console.log("✅ 登录成功\n");

  let total = 0;
  let success = 0;
  let skipped = 0;
  let filtered = 0;

  try {
    for await (const file of client.iterFiles()) {
      if (!file.id) continue;

      total++;

      // 标题过滤：跳过临时通知
      const { keep, reason } = shouldKeep(file.title);
      if (!keep) {
        if (total % 20 === 0) console.log(`[${total}] ⏭️ 过滤: ${file.title.slice(0, 40)} (${reason})`);
        filtered++;
        continue;
      }

      console.log(`[${total}] ${file.department}: ${file.title.slice(0, 50)} (${file.date})`);

      try {
        const detail = await client.getFileDetail(file.id);
        const ok = await sendToBackend({
          id: file.id,
          title: detail.title || file.title,
          department: file.department,
          date: file.date,
          rawHtml: detail.rawHtml,
        });
        if (ok) success++;
        else skipped++;
      } catch (err: any) {
        console.error(`  ⚠️  获取详情失败: ${err.message}`);
        skipped++;
      }

      await new Promise((r) => setTimeout(r, 300));
    }
  } finally {
    client.close();
  }

  console.log(`\n📊 完成! 总计: ${total}, 已索引: ${success}, 过滤跳过: ${filtered}, 失败: ${skipped}`);
}

main().catch((err) => {
  console.error("❌ 致命错误:", err.message);
  process.exit(1);
});

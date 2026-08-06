/**
 * Incremental Sync — only crawl files newer than the last sync time.
 *
 * Usage:
 *   cd scripts && npm run sync
 *
 * Environment variables:
 *   WJXT_USERNAME  — student ID
 *   WJXT_PASSWORD  — password
 *   BACKEND_URL    — FastAPI backend URL (default: http://localhost:8000)
 *
 * The backend dedupes by content hash: unchanged files are skipped,
 * updated files (policy revisions) are re-indexed automatically.
 */

import { WjxtClient } from "gxu-wjxt";
import * as fs from "fs";
import * as path from "path";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const USERNAME = process.env.WJXT_USERNAME || "";
const PASSWORD = process.env.WJXT_PASSWORD || "";

// 上次同步时间记录文件
const LAST_SYNC_FILE = path.join(__dirname, "..", "data", "last_sync.json");

if (!USERNAME || !PASSWORD) {
  console.error("❌ 请设置环境变量: WJXT_USERNAME 和 WJXT_PASSWORD");
  process.exit(1);
}

// ============ 标题过滤规则（与 ingest.ts 保持一致） ============

const KEEP_PATTERNS = [
  /实施办法/, /管理办法/, /管理规定/, /工作办法/, /条例/, /制度/,
  /规定$/, /办法$/, /细则/, /指导意见/, /实施方案/, /评审办法/, /评定办法/,
  /推荐.*免试.*研究生/, /推免/, /保研/, /培养方案/, /教学计划/, /校历/,
  /学籍.*规定/, /学位.*办法/, /导师制/, /毕业论文.*规定/, /创新创业.*学分/,
  /交流生.*办法/, /本研一体化/, /学生资助政策/, /国家奖助学金.*评审管理/,
  /学生奖励办法/, /学生处分规定/, /转专业.*办法/, /转专业.*通知$/,
  /专业分流.*通知/, /辅修.*办法/, /微专业/, /免试认定/,
];

const DISCARD_PATTERNS = [
  // 基建后勤临时通知
  /停电/, /停水/, /施工/, /消杀/, /病虫害/, /道路封闭/,
  /临时(占用|管控|封闭)/, /倒闸/, /错峰用电/, /限制使用/,
  /短时停电/, /停气/, /交通管制/, /占道/, /封闭道路/,
  /封闭.*道路/, /路灯运行/, /空调(清洗|消毒|限)/, /物业费/,
  /封闭.*(路段|车道|道路)/, /临时封闭/,
  // 考务
  /(四、六级|四六级)考试.*(准考证|报名|听力|测试)/,
  /英语四、六级.*(准考证|报名)/,
  // 征文/作品征集
  /征文/, /关于征集.*作品/, /关于.*作品征集/,
  // 选拔运动员
  /关于选拔.*运动员/,
  // 个人行政决定
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
  /关于表彰.*的决定/, /关于聘任.*的通知/, /关于.*换届任职/,
  /关于公布.*名单/, /关于公布.*获奖名单/, /关于.*评选结果的公示/,
  /关于.*推荐名单/, /关于.*拟推荐/, /关于.*名单的公示/,
  // 宿舍
  /学生宿舍未按时熄灯/, /学生宿舍安全.*抽检/, /宿舍.*情况通报/,
  // 转发
  /转发.*的通知$/,
  // 活动/比赛
  /关于举办.*大赛/, /关于举办.*比赛/, /关于举行.*比赛/, /关于举办.*活动/,
  /关于组织参加.*大赛/, /关于组织参加.*竞赛/, /关于组织.*参赛/,
  // 党建通讯
  /党建通讯/, /简报/,
  // 节假日
  /关于调整.*放假.*教学安排/, /关于.*元旦.*放假/, /关于.*劳动节.*放假/,
  // 讲座培训
  /关于举办.*讲座/, /关于举办.*培训/, /关于举办.*报告会/, /关于举办.*训练营/,
  // 学期考务/晚自习
  /关于.*学期.*考试安排/, /关于.*学期.*晚自习/,
  // 用能
  /用能(巡查|抽查)/, /用电情况/,
  // 废弃车/烟花爆竹
  /废弃车/, /烟花爆竹/,
  // 项目名单
  /关于公布.*项目.*名单/, /关于公布.*立项/,
  // 团组织
  /关于同意共青团.*选举结果/, /关于.*团委.*更名/,
  // 校运会单项
  /关于举行.*校运会/, /关于举行.*篮球赛/, /关于举行.*气排球/,
  /关于举行.*足球/, /关于举行.*网球/, /关于举行.*羽毛球/, /关于举行.*跳绳/,
  // 毕业生
  /关于.*毕业生.*办理/, /关于.*毕业.*离校/, /关于.*征兵/,
  // 新生入馆
  /新生.*入馆教育/,
  // 团评优
  /关于表彰.*共青团/, /关于表彰.*团员/, /关于表彰.*志愿/,
  // 奖学金具体名单
  /(奖学金|助学金|资助).*评选结果公示/,
  /(奖学金|助学金|资助).*推荐名单公示/,
  /关于颁发.*奖学金的决定$/,
  /关于颁发.*助学金的决定$/,
  /关于颁发.*基金的决定$/,
];

function shouldKeep(title: string): boolean {
  for (const p of KEEP_PATTERNS) if (p.test(title)) return true;
  for (const p of DISCARD_PATTERNS) if (p.test(title)) return false;
  return true; // 默认保留
}

// ============ last_sync 读写 ============

function readLastSync(): Date | null {
  try {
    if (fs.existsSync(LAST_SYNC_FILE)) {
      const data = JSON.parse(fs.readFileSync(LAST_SYNC_FILE, "utf-8"));
      if (data.lastSync) return new Date(data.lastSync);
    }
  } catch {
    // 忽略损坏的记录
  }
  return null;
}

function writeLastSync(date: Date) {
  fs.mkdirSync(path.dirname(LAST_SYNC_FILE), { recursive: true });
  fs.writeFileSync(LAST_SYNC_FILE, JSON.stringify({ lastSync: date.toISOString() }, null, 2));
}

// ============ 发送到后端 ============

async function sendToBackend(file: {
  id: number;
  title: string;
  department: string;
  date: string;
  rawHtml: string;
}): Promise<boolean> {
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
    console.error(`  ⚠️  后端错误 ${res.status}: ${text.slice(0, 150)}`);
    return false;
  }
  const data = (await res.json()) as { message?: string };
  console.log(`  ✅ ${data.message}`);
  return true;
}

// ============ 主流程 ============

async function main() {
  console.log("🔄 开始增量同步...\n");

  const lastSync = readLastSync();
  if (!lastSync) {
    console.log("⚠️  未找到上次同步记录。");
    console.log("   如果是首次运行，增量同步会跳过所有已有文件（不处理历史）。");
    console.log("   如需全量导入，请使用 npm run ingest。");
  } else {
    console.log(`上次同步时间: ${lastSync.toLocaleString("zh-CN")}`);
  }
  console.log("");

  const client = new WjxtClient({ username: USERNAME, password: PASSWORD });
  const loggedIn = await client.login();
  if (!loggedIn) {
    console.error("❌ 登录失败，请检查用户名和密码");
    process.exit(1);
  }
  console.log("✅ 登录成功\n");

  let total = 0;
  let indexed = 0;
  let filtered = 0;
  let skipped = 0;
  let stopped = false;

  try {
    for await (const file of client.iterFiles()) {
      if (!file.id) continue;
      total++;

      // 日期判断：文件系统按时间倒序，遇到早于上次同步的即停止
      if (lastSync && file.date) {
        const fileDate = new Date(file.date);
        if (!isNaN(fileDate.getTime()) && fileDate < lastSync) {
          console.log(`\n⏹️  遇到 ${file.date}（早于上次同步 ${lastSync.toISOString().slice(0, 10)}），停止遍历`);
          stopped = true;
          break;
        }
      }

      // 标题过滤
      if (!shouldKeep(file.title)) {
        filtered++;
        continue;
      }

      // 发送到后端（后端按 hash 去重：未变跳过，变更重建）
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
        if (ok) indexed++;
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

  // 无论是否遇到停止点，都更新 last_sync 为当前时间
  // （这样下次只处理更新的文件；如果本次因网络中断，下次会从头但依赖后端去重）
  writeLastSync(new Date());

  console.log(`\n📊 同步完成!`);
  console.log(`   扫描: ${total} 个文件`);
  console.log(`   已索引: ${indexed} | 过滤跳过: ${filtered} | 失败: ${skipped}`);
  console.log(`   提前停止: ${stopped ? "是（已到上次同步点）" : "否（遍历完）"}`);
  console.log(`\n下次同步将只处理 ${new Date().toLocaleString("zh-CN")} 之后的文件`);
}

main().catch((err) => {
  console.error("❌ 致命错误:", err.message);
  process.exit(1);
});

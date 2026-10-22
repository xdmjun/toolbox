#!/usr/bin/env node
/**
 * evidence-guard — 用户消息提交后注入「先取证再断言」铁律
 * 事件: user_prompt_submit
 * 协议: stdout 纯文本 → 作为 additionalContext 追加到用户消息后（atomcode hook 协议）
 * 设计: 无条件每轮注入，防模型凭推断断言用户环境能力（渲染效果/软件行为/文件状态）
 */
const TIME = () => {
  const d = new Date();
  const p = n => String(n).padStart(2, '0');
  const wd = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()];
  return `【当前时间】${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} 周${wd} ${p(d.getHours())}:${p(d.getMinutes())} —— 涉及「今天/明天/剩余天数」的表述一律以此为准，禁止沿用上一轮的日期假设；日期表述与此前对话冲突时，以本条时间为准。`;
};

const GUI = '【取证铁律】对用户环境/外部事实的断言必须有证据，禁止类推：\n' +
  '1) 「用户 Obsidian/webUI 能否渲染某语法」→ 先 grep 库里既有 md 找同款先例，有先例才允许用；无先例时明说「未验证」。\n' +
  '2) 「文件里有什么、代码怎么写的」→ 必须 read_file/grep 读过再说，禁止凭记忆或模式推测 API/签名/路径。\n' +
  '3) 任何「应该是/大概是/按理说」式判断都视为未验证——要么去查，要么明确标注不确定。\n' +
  '4) 被用户指出「你确认过吗/你猜的吧」时，如实承认未验证，立即去取证，不辩解。\n' +
  '5) 目标定位以用户原话为准：用户提到的模块/文件/主题名词是唯一定位依据；搜索结果只是线索，与原话冲突时以原话为准。对涉及用户口语指代文件/笔记的修改，动手前先复述目标（「你指的是 XX 文件吗」）确认。';

let buf = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', d => (buf += d));
process.stdin.on('end', () => {
  const out = TIME() + '\n' + GUI;
  process.stdout.write(out + '\n');
  process.exit(0);
});
// stdin 异常也照样注入，fail-open
setTimeout(() => { const out = TIME() + '\n' + GUI; process.stdout.write(out + '\n'); process.exit(0); }, 500).unref();
